"""Compare 0x520c20 updates with only environment stage 0x51e940 isolated."""
import argparse
import random
import struct
from pathlib import Path

from client.world_object_physics_step import RECORD_SIZE, step_world_object_physics
from client.contact_force import contact_forces_step
from tools.native_oracle import DynoOracle


def verify(executable, native_runner=None, native_case_limit=7):
    from unicorn import UC_HOOK_CODE

    oracle = DynoOracle(executable)
    cpu, reg = oracle.cpu, oracle.reg
    owner = 0x0092C478

    def isolate_children(machine, address, _size, _data):
        if address == 0x0051E940:
            stack = machine.reg_read(reg.UC_X86_REG_ESP)
            return_address = struct.unpack('<I', machine.mem_read(stack, 4))[0]
            machine.reg_write(reg.UC_X86_REG_ESP, stack + 4)
            machine.reg_write(reg.UC_X86_REG_EIP, return_address)

    cpu.hook_add(UC_HOOK_CODE, isolate_children,
                 begin=0x0051E940, end=0x0051E940)

    cases = (
        (False, 0, False, True, False, 0, 0.0),
        (False, 0, False, True, False, 1, 0.0),
        (False, 0, False, True, True, 0, 0.0),
        (False, 0, False, True, False, 0, 1.0),
        (False, 0, False, False, False, 0, 0.0),
        (True, 1, True, True, False, 0, 0.0),
        (True, 0, True, True, False, 0, 0.0),
    )
    rng = random.Random(0x520C20)
    cases = list(cases)
    for _ in range(128):
        cases.append((bool(rng.randrange(2)), rng.randrange(2),
                      bool(rng.randrange(2)), bool(rng.randrange(2)),
                      bool(rng.randrange(2)), rng.choice((-1, 0, 1, 32, 33)),
                      rng.choice((0.0, 1.0))))

    native_cases = 0
    for case_index, (mode_active, mode_number, object_mode_flag, active,
                     special, contacts, acceleration_gate) in enumerate(cases):
        record = bytearray(RECORD_SIZE)
        struct.pack_into('<I', record, 0, 1)
        record[4] = int(active)
        record[6] = int(object_mode_flag)
        record[7] = int(special)
        struct.pack_into('<3f', record, 0x14, 1.25, -2.5, 0.75)
        struct.pack_into('<3f', record, 0x38, 0.125, -0.25, 0.5)
        struct.pack_into('<f', record, 0x6c, acceleration_gate)
        struct.pack_into('<h', record, 0x3bc, contacts)
        basis = ((0.75, 0.125, -0.25, 0.5, 1.0, 0.25,
                  -0.125, 0.375, 0.875) if case_index < 7 else
                 tuple(rng.uniform(-2, 2) for _ in range(9)))
        struct.pack_into('<9f', record, 0x31c, *basis)
        struct.pack_into('<f', record, 0x50, rng.uniform(0, 5))
        struct.pack_into('<3f', record, 0x2f0,
                         *(rng.uniform(0, 3) for _ in range(3)))
        for offset in (0x248,0x254,0x260,0x26c,0x278,0x284):
            struct.pack_into('<3f',record,offset,
                             rng.uniform(.5,2),rng.uniform(-.5,.5),rng.uniform(-.5,.5))
        for offset in (0x54,0x2fc,0x300,0x304,0x308,0x30c,0x310,0x314,
                       0xd0,0xcc,0xd4,0x9c,0xa0,0xa4,0xa8,0xac,0xb0,
                       0xb4,0xb8,0xbc):
            struct.pack_into('<f',record,offset,rng.uniform(.25,2))

        cpu.mem_write(owner, bytes(record))
        cpu.mem_write(0x00AA459C, struct.pack('<B', int(mode_active)))
        cpu.mem_write(0x00A6CC40, struct.pack('<I', mode_number))
        oracle.call(0x00520C20, (owner,))
        original = bytes(cpu.mem_read(owner, RECORD_SIZE))

        translated = bytearray(record)
        step_world_object_physics(translated, mode_active=mode_active,
                                  mode_number=mode_number,
                                  environment_step=lambda _: None,
                                  contact_force_step=contact_forces_step)
        if original != translated:
            differences = [i for i, (left, right) in
                           enumerate(zip(original, translated)) if left != right]
            raise AssertionError(f'0x520c20 mismatch at bytes '
                                 f'{[hex(i) for i in differences[:16]]}; '
                                 f'original={original[differences[0]:differences[0]+4].hex()} '
                                 f'translated={translated[differences[0]:differences[0]+4].hex()}')
        if native_runner is not None and case_index < native_case_limit:
            import subprocess
            result = subprocess.run([str(native_runner)],
                input=f'{int(mode_active)} {mode_number} {bytes(record).hex()}\n',
                text=True, capture_output=True, check=True)
            native = bytes.fromhex(result.stdout.strip())
            if native != original:
                differences = [i for i, (left, right) in
                               enumerate(zip(original, native)) if left != right]
                raise AssertionError(f'native 0x520c20 mismatch in case {case_index} at '
                                     f'{[hex(i) for i in differences[:16]]}; '
                                     f'original={[(hex(i),original[i:i+4].hex()) for i in differences[:16]]}; '
                                     f'native={[(hex(i),native[i:i+4].hex()) for i in differences[:16]]}')
            native_cases += 1
    return len(cases), native_cases


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', type=Path)
    parser.add_argument('--native-runner', type=Path)
    parser.add_argument('--native-case-limit', type=int, default=7)
    args = parser.parse_args()
    python_cases, native_cases = verify(args.executable, args.native_runner,
                                        args.native_case_limit)
    print(f'Python owned 0x520c20 state updates match for {python_cases} cases; '
          f'native comparison matches for {native_cases} curated cases '
          '(0x51e940 isolated; 0x51fc00 runs translated)')


if __name__ == '__main__':
    main()
