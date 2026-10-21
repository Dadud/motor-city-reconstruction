"""Compare the 0x43bfd0 wrapper with its two stateful children isolated."""
import argparse
import random
import struct
from pathlib import Path

from client.environment_correction import correct_surface_collision
from tools.native_oracle import DynoOracle


def verify(executable):
    from unicorn import UC_HOOK_CODE

    oracle = DynoOracle(executable)
    cpu, reg = oracle.cpu, oracle.reg
    owner = 0x71005000

    def isolate_children(machine, address, _size, _data):
        if address in (0x0043BA40, 0x0043B750):
            stack = machine.reg_read(reg.UC_X86_REG_ESP)
            return_address = struct.unpack('<I', machine.mem_read(stack, 4))[0]
            machine.reg_write(reg.UC_X86_REG_ESP, stack + 4)
            machine.reg_write(reg.UC_X86_REG_EIP, return_address)

    cpu.hook_add(UC_HOOK_CODE, isolate_children,
                 begin=0x0043BA40, end=0x0043B750)
    rng = random.Random(0x43BFD0)
    for case in range(96):
        record = bytearray(rng.randbytes(0x4F8))
        y = rng.uniform(-200, 200)
        status = rng.choice((0, 1, -1, 17))
        step = rng.uniform(-30, 30)
        struct.pack_into('<f', record, 0x0C, y)
        struct.pack_into('<i', record, 0x36C, status)
        cpu.mem_write(owner, bytes(record))
        cpu.mem_write(0x0098C470, struct.pack('<f', step))
        oracle.call(0x0043BFD0, (owner, case % 64))
        original = bytes(cpu.mem_read(owner, len(record)))
        translated = bytearray(record)
        correct_surface_collision(translated, case % 64, vertical_step=step,
                                  adjust_contact=lambda *_: None,
                                  reset_vehicle_state=lambda _: None)
        if original != translated:
            raise AssertionError(f'0x43bfd0 record mismatch in case {case}')
    return 96


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', type=Path)
    args = parser.parse_args()
    print(f'0x43bfd0 wrapper matches the original for {verify(args.executable)} cases; '
          '0x43ba40 and 0x43b750 are isolated')


if __name__ == '__main__':
    main()
