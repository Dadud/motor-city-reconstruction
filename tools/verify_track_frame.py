"""Compare both 0x42df00 frame-selection branches against original instructions."""
import argparse
import random
import struct
from pathlib import Path

from client.track_frame import track_frame
from tools.native_oracle import DynoOracle


def verify(executable):
    oracle = DynoOracle(executable)
    cpu = oracle.cpu
    table, query_address, point_address, frame_address = 0x71000000, 0x71002000, 0x71003000, 0x71004000
    cpu.mem_write(0x0097C38C, struct.pack('<I', table))
    rng = random.Random(0x42DF00)
    for case in range(80):
        query = bytearray(0x44)
        rows = []
        if case < 40:
            row = tuple(rng.uniform(-20, 20) for _ in range(21))
            rows.append(row)
            struct.pack_into('<17I', query, 0, 0, 0, int(case == 0), 0, *([0] * 13))
            cpu.mem_write(table, struct.pack('<21f', *row))
            reference = None
        else:
            first = tuple(rng.uniform(-5, 5) for _ in range(3))
            second = tuple(rng.uniform(-5, 5) for _ in range(3))
            reference = tuple(rng.uniform(-20, 20) for _ in range(3))
            struct.pack_into('<I', query, 12, 1)
            struct.pack_into('<I', query, 16, point_address)
            struct.pack_into('<6f', query, 44, *first, *second)
            cpu.mem_write(point_address, struct.pack('<3f', *reference))
        cpu.mem_write(query_address, bytes(query))
        cpu.mem_write(frame_address, bytes(36))
        oracle.call(0x0042DF00, (point_address + 0x100, query_address, frame_address))
        actual_point = bytes(cpu.mem_read(point_address + 0x100, 12))
        actual_frame = bytes(cpu.mem_read(frame_address, 36))
        expected_point, expected_frame = track_frame(query, rows, reference)
        if actual_point != struct.pack('<3f', *expected_point):
            raise AssertionError(f'0x42df00 reference point mismatch in case {case}')
        if actual_frame != struct.pack('<9f', *expected_frame):
            raise AssertionError(f'0x42df00 frame mismatch in case {case}')
    return 80


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', type=Path)
    args = parser.parse_args()
    print(f'0x42df00 track-frame output matches the original for {verify(args.executable)} cases')


if __name__ == '__main__':
    main()
