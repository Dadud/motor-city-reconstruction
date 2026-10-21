"""Compare the 0x51e460 track-frame setup with the original binary."""
import argparse
import random
import struct
from pathlib import Path

from client.world_object_contact import prepare_contact_frame
from tools.native_oracle import DynoOracle


PATHS = 0x71001000
RECORD = 0x72002000
POSITION = 0x71003000
STOP_AFTER_ENVIRONMENT = 0x51E7D5


def _row(rng):
    row = [0.0] * 21
    row[:3] = [rng.uniform(-50, 50) for _ in range(3)]
    # Distinct non-axis-aligned rows stress normalization, basis conversion,
    # and the orientation branches without degeneracy.
    row[3:6] = [0.5, 1.25, -0.75]
    row[6:9] = [-1.5, 0.25, 2.0]
    row[9:12] = [1.0, -0.5, 1.75]
    return tuple(struct.unpack('<f', struct.pack('<f', value))[0]
                 for value in row)


def verify(executable, cases=96):
    from unicorn import UC_HOOK_CODE

    oracle = DynoOracle(executable)
    cpu, reg = oracle.cpu, oracle.reg
    rng = random.Random(0x51E460)
    maximum_error = 0.0
    float_offsets = (set(range(8, 20, 4)) | set(range(0x78, 0xc0, 4))
                     | set(range(0x31c, 0x340, 4))
                     | set(range(0x358, 0x364, 4)) | {0x3b8})
    modes = (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 16)
    for case in range(cases):
        row = _row(rng)
        rows = (row,)
        path_image = struct.pack('<21f', *row)
        cpu.mem_write(PATHS, path_image)
        cpu.mem_write(0x0097C38C, struct.pack('<I', PATHS))

        initial = bytearray(rng.randbytes(0x4f8))
        # Make every coordinate and matrix value finite and stable; retain
        # unrelated state as distinct bytes so accidental writes are visible.
        for offset in (8, 12, 16):
            struct.pack_into('<f', initial, offset, rng.uniform(-10, 10))
        for index in range(9):
            struct.pack_into('<f', initial, 0x78 + index * 4,
                             rng.uniform(-1, 1))
        position = tuple(rng.uniform(-20, 20) for _ in range(3))
        flags = modes[case % len(modes)]
        if case & 1:
            # Choose a negative local X on alternating bit-4 cases to cover
            # the signed-orientation split in child 0x51e2d0.
            position = (row[0] - 10.0, row[1] + 3.0, row[2] - 2.0)
            flags |= 0x4
        position_image = struct.pack('<3f', *position)
        cpu.mem_write(RECORD, bytes(initial))
        cpu.mem_write(POSITION, position_image)
        stopped = []

        def intercept(machine, address, _size, _data):
            if address == 0x0051E940:
                stack = machine.reg_read(reg.UC_X86_REG_ESP)
                ret = struct.unpack('<I', machine.mem_read(stack, 4))[0]
                machine.reg_write(reg.UC_X86_REG_ESP, stack + 4)
                machine.reg_write(reg.UC_X86_REG_EIP, ret)
            elif address == STOP_AFTER_ENVIRONMENT:
                stopped.append(True)
                machine.reg_write(reg.UC_X86_REG_EIP, oracle.stop)

        hook = cpu.hook_add(UC_HOOK_CODE, intercept)
        try:
            oracle.call(0x0051E460, (RECORD, 0, POSITION, flags),
                        instruction_limit=500000)
        finally:
            cpu.hook_del(hook)
        if not stopped:
            raise AssertionError(f'case {case} did not reach the environment-call boundary')
        original = bytes(cpu.mem_read(RECORD, 0x4f8))

        translated = bytearray(initial)
        prepare_contact_frame(translated, rows, 0, position, flags)
        for offset in range(0, 0x4f8, 4):
            actual_word = original[offset:offset + 4]
            expected_word = translated[offset:offset + 4]
            if actual_word == expected_word:
                continue
            if offset in float_offsets:
                actual = struct.unpack('<f', actual_word)[0]
                expected = struct.unpack('<f', expected_word)[0]
                error = abs(actual - expected)
                maximum_error = max(maximum_error, error)
                if error <= 1e-5:
                    continue
            raise AssertionError(
                f'0x51e460 prefix mismatch case={case} flags={flags:#x} '
                f'offset={offset:#x} native={actual_word.hex()} '
                f'python={expected_word.hex()}')
    return cases, maximum_error


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', type=Path)
    parser.add_argument('--cases', type=int, default=96)
    args = parser.parse_args()
    cases, error = verify(args.executable, args.cases)
    print(f'0x51e460 track-frame prefix matches {cases} original cases; '
          f'maximum compared float-field error {error:.9g}')


if __name__ == '__main__':
    main()
