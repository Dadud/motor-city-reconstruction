"""Compare the deterministic prefix of 0x549660 before its virtual call."""
import argparse
import random
import struct
from pathlib import Path

from client.world_object_reset import OWNER_SIZE, reset_world_object_drive_prefix
from tools.native_oracle import DynoOracle

OWNER = 0x72002000
PROFILE = 0x71005000
INTERFACE = 0x71006000
VTABLE = 0x71006100
VIRTUAL_STOP = 0x7000FFE0


def verify(executable, cases=96):
    from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_INVALID

    oracle = DynoOracle(executable)
    cpu, reg = oracle.cpu, oracle.reg
    rng = random.Random(0x549660)
    float_offsets = {0xb5c, 0xb60, 0xab0, 0xabc, 0xad4, 0xadc, 0xacc}
    maximum_float_error = 0.0
    for case in range(cases):
        record = bytearray(rng.randbytes(OWNER_SIZE))
        profile = bytearray(rng.randbytes(0x690))
        struct.pack_into('<I', record, 0x1c94, PROFILE)
        profile_mode = case % 2
        struct.pack_into('<I', profile, 0x68c, profile_mode)
        struct.pack_into('<f', profile, 0x374, rng.uniform(0.1, 5.0))
        struct.pack_into('<I', profile, 0x6c, rng.randrange(0, 5000))
        # The divide operands are intentionally finite and nonzero.
        struct.pack_into('<f', record, 0x18ec, rng.uniform(1, 100))
        struct.pack_into('<f', record, 0x18f0, rng.uniform(1, 100))
        struct.pack_into('<i', record, 0xac0, rng.choice((-12, -3, 1, 7, 24)))
        struct.pack_into('<f', record, 0x1898, rng.uniform(-500, 500))
        struct.pack_into('<f', record, 0x1894, rng.uniform(-500, 500))
        struct.pack_into('<f', record, 0xad4, rng.uniform(0.0, 1.5))
        struct.pack_into('<f', record, 0xadc, rng.uniform(-2, 30))
        struct.pack_into('<f', record, 0xacc, rng.uniform(-2, 30))
        drive_flags = (rng.getrandbits(32) & 0xfffffffe) | (case & 1)
        struct.pack_into('<I', record, 0xae4, drive_flags)
        cpu.mem_write(OWNER, bytes(record))
        cpu.mem_write(PROFILE, bytes(profile))
        cpu.mem_write(0x00A65BD0, struct.pack('<I', INTERFACE))
        cpu.mem_write(INTERFACE, struct.pack('<I', VTABLE))
        cpu.mem_write(VTABLE + 0x10, struct.pack('<I', VIRTUAL_STOP))
        reset_status = (case // 2) & 1
        reached_virtual = []
        invalid_memory = []

        def invalid_access(machine, access, address, size, value, _data):
            invalid_memory.append((address, size, access, value))
            return False

        def isolate_state_child(machine, address, _size, _data):
            if address == 0x0043B570:
                stack = machine.reg_read(reg.UC_X86_REG_ESP)
                return_address = struct.unpack('<I', machine.mem_read(stack, 4))[0]
                machine.reg_write(reg.UC_X86_REG_EAX, reset_status)
                machine.reg_write(reg.UC_X86_REG_ESP, stack + 4)
                machine.reg_write(reg.UC_X86_REG_EIP, return_address)
            elif address == VIRTUAL_STOP:
                reached_virtual.append(True)
                machine.reg_write(reg.UC_X86_REG_EIP, oracle.stop)

        hook = cpu.hook_add(UC_HOOK_CODE, isolate_state_child)
        bad_hook = cpu.hook_add(UC_HOOK_MEM_INVALID, invalid_access)
        try:
            try:
                oracle.call(0x00549660, (OWNER,), instruction_limit=500000)
            except Exception as error:
                eip = cpu.reg_read(reg.UC_X86_REG_EIP)
                raise RuntimeError(f'fault case {case} at {eip:#x}, '
                                   f'memory={invalid_memory}') from error
        finally:
            cpu.hook_del(hook)
            cpu.hook_del(bad_hook)
        if not (drive_flags & 1) and not reached_virtual:
            raise AssertionError(f'case {case} did not reach virtual-call boundary')
        original = bytes(cpu.mem_read(OWNER, OWNER_SIZE))
        translated = bytearray(record)
        reset_world_object_drive_prefix(translated, profile,
            reset_drive_state=lambda _: reset_status)
        differences = []
        for offset in range(0, OWNER_SIZE, 4):
            left, right = original[offset:offset + 4], translated[offset:offset + 4]
            if left == right:
                continue
            if offset in float_offsets:
                left_value, right_value = struct.unpack('<f', left)[0], struct.unpack('<f', right)[0]
                error = abs(left_value - right_value)
                maximum_float_error = max(maximum_float_error, error)
                if error <= 5e-6:
                    continue
            differences.extend(i for i in range(offset, offset + 4) if left[i-offset] != right[i-offset])
        if differences:
            raise AssertionError(f'0x549660 prefix mismatch case {case}; '
                                 f'bytes {[hex(i) for i in differences[:24]]}; '
                                 f'original={[(hex(i), original[i:i+4].hex()) for i in differences[:12]]}; '
                                 f'python={[(hex(i), translated[i:i+4].hex()) for i in differences[:12]]}')
    return cases, maximum_float_error


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', type=Path)
    parser.add_argument('--cases', type=int, default=96)
    args = parser.parse_args()
    count, maximum_error = verify(args.executable, args.cases)
    print(f'0x549660 pre-virtual-call writes match {count} original records; '
          f'maximum float error {maximum_error:.9g}; '
          '0x43b570 and the interface result use controlled return bridges')


if __name__ == '__main__':
    main()
