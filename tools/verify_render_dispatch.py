"""Verify the state-save and callback arguments of 0x6f1320."""
import argparse
from pathlib import Path
import struct

from tools.native_oracle import DynoOracle


def verify(executable):
    from unicorn import UC_HOOK_CODE
    oracle = DynoOracle(executable)
    old_matrix, old_position, old_count = 0x71001000, 0x71002000, 7
    destination, matrix, position, points = 0x71003000, 0x71004000, 0x71005000, 0x71006000
    for address, value in ((0x00b368c8, old_matrix), (0x00b368c4, old_position),
                           (0x008c89f8, old_count), (0x008c89f0, 0x1234),
                           (0x00b368ec, 0), (0x00b368e8, 0)):
        oracle.cpu.mem_write(address, struct.pack('<I', value))
    observed = []
    def intercept(cpu, pc, size, user):
        esp = cpu.reg_read(oracle.reg.UC_X86_REG_ESP)
        return_to, *args = struct.unpack('<5I', cpu.mem_read(esp, 20))
        observed.append(tuple(args))
        cpu.reg_write(oracle.reg.UC_X86_REG_ESP, esp+4)
        cpu.reg_write(oracle.reg.UC_X86_REG_EIP, return_to)
    hook = oracle.cpu.hook_add(UC_HOOK_CODE, intercept,
                               begin=0x006f28f0, end=0x006f28f0)
    try:
        oracle.call(0x006f1320, (0x16, destination, matrix, position, points, 12))
    finally:
        oracle.cpu.hook_del(hook)
    expected = [(6, 0x16, destination, points)]
    if observed != expected:
        raise AssertionError(f'draw dispatch arguments mismatch: {observed!r}')
    for address, value in ((0x00b368c8, old_matrix), (0x00b368c4, old_position),
                           (0x008c89f8, old_count), (0x00b368ec, 1), (0x00b368e8, 1)):
        actual = struct.unpack('<I', oracle.cpu.mem_read(address, 4))[0]
        if actual != value:
            raise AssertionError(f'render state at 0x{address:x}: {actual:#x} != {value:#x}')
    return 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', type=Path)
    args = parser.parse_args()
    print(f'0x6f1320 state wrapper matches for {verify(args.executable)} case')


if __name__ == '__main__':
    main()
