"""Compare native track-row signed-distance status helpers."""
import argparse
import json
import random
import struct

from client.track_surface_query import (track_row_has_type_two,
    track_row_side_status)
from tools.native_oracle import DynoOracle


POINT, TRACKS = 0x71000100, 0x71001000


def verify(executable, cases=512):
    if type(cases) is not int or not 1 <= cases <= 10_000:
        raise ValueError('cases must be between 1 and 10000')
    oracle = DynoOracle(executable)
    rng = random.Random(0x42E0A0)
    for case in range(cases):
        count = 1 + case % 16
        rows = []
        for index in range(count):
            row = bytearray(rng.getrandbits(8) for _ in range(0x54))
            struct.pack_into('<3f', row, 0,
                             *(rng.uniform(-1000., 1000.) for _ in range(3)))
            struct.pack_into('<3f', row, 0x24,
                             *(rng.uniform(-4., 4.) for _ in range(3)))
            row[0x50] = rng.randrange(256)
            row[0x51] = rng.randrange(256)
            rows.append(bytes(row))
        index = case % count
        origin = struct.unpack_from('<3f', rows[index])
        normal = struct.unpack_from('<3f', rows[index], 0x24)
        branch = case % 4
        if branch == 0:
            point = origin
        elif branch == 1:
            point = tuple(a + b for a, b in zip(origin, normal))
        elif branch == 2:
            point = tuple(a - b for a, b in zip(origin, normal))
        else:
            point = tuple(rng.uniform(-1000., 1000.) for _ in range(3))
        point = struct.unpack('<3f', struct.pack('<3f', *point))
        expected_status = track_row_side_status(point, rows, index)
        expected_predicate = track_row_has_type_two(point, rows, index)
        oracle._reset()
        oracle.cpu.mem_write(POINT, struct.pack('<3f', *point))
        oracle.cpu.mem_write(TRACKS, b''.join(rows))
        oracle.cpu.mem_write(0x0097C38C, struct.pack('<I', TRACKS))
        oracle.call(0x42E0A0, (POINT, index), instruction_limit=100_000)
        actual_status = oracle.cpu.reg_read(oracle.reg.UC_X86_REG_EAX) & 0xff
        if actual_status != expected_status:
            raise AssertionError(
                f'case {case}: 0x42e0a0 native={actual_status:#x} port={expected_status:#x}')
        oracle.call(0x42E160, (POINT, index), instruction_limit=100_000)
        actual_predicate = oracle.cpu.reg_read(oracle.reg.UC_X86_REG_EAX) & 0xff
        if actual_predicate != int(expected_predicate):
            raise AssertionError(
                f'case {case}: 0x42e160 native={actual_predicate} '
                f'port={int(expected_predicate)}')
    return {'cases': cases, 'entry_0x42e0a0': cases, 'entry_0x42e160': cases,
            'scope': 'complete low-byte returns for signed plane distance, zero boundary, and both status bytes'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    parser.add_argument('--cases', type=int, default=512)
    args = parser.parse_args()
    print(json.dumps(verify(args.executable, args.cases)))


if __name__ == '__main__':
    main()
