"""Compare track-side surface selection against original 0x42e230."""
import argparse
import random
import struct
from pathlib import Path

from client.surface_selector import select_surface
from tools.native_oracle import DynoOracle


def verify(executable):
    oracle = DynoOracle(executable)
    cpu = oracle.cpu
    table, query_address = 0x71005000, 0x71002000
    position_address, descriptor_address = 0x71003000, 0x71004000
    cpu.mem_write(0x0097C38C, struct.pack('<I', table))
    rng = random.Random(0x42E230)
    rows = []
    for _ in range(64):
        row = bytearray(0x54)
        values = tuple(rng.uniform(-100, 100) for _ in range(12))
        struct.pack_into('<12f', row, 0, *values)
        row[0x50:0x52] = bytes((rng.randrange(4), rng.randrange(4)))
        rows.append(bytes(row))
    for case in range(192):
        index = case % len(rows)
        position = tuple(rng.uniform(-20, 20) for _ in range(3))
        query = bytearray(0x44)
        flags = None
        if case % 3 == 0:
            struct.pack_into('<I', query, 12, descriptor_address)
            flags = rng.randrange(256)
            cpu.mem_write(descriptor_address, bytes(4) + bytes((flags,)) + bytes(3))
        cpu.mem_write(table + index * 0x54, rows[index])
        cpu.mem_write(query_address, bytes(query))
        cpu.mem_write(position_address, struct.pack('<3f', *position))
        oracle.call(0x0042E230, (position_address, index, query_address))
        original = cpu.reg_read(oracle.reg.UC_X86_REG_EAX) & 0xFF
        expected = int(select_surface(position, index, query, rows, flags))
        if original != expected:
            raise AssertionError(f'0x42e230 mismatch in case {case}: original={original}, expected={expected}')
    return 192


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', type=Path)
    args = parser.parse_args()
    print(f'0x42e230 surface selection matches the original for {verify(args.executable)} cases')


if __name__ == '__main__':
    main()
