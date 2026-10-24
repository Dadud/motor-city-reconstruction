"""Compare block-row membership lookup with the original MCO routine."""
import argparse
import json
import random
import struct

from client.track_block_membership import (ID_OFFSET, ID_SLOT_STRIDE,
    ROW_STRIDE, contains_track_block_id)
from tools.native_oracle import DynoOracle


TABLE, RESULT = 0x71004000, 0x7100F000


def verify(executable, cases=512):
    if type(cases) is not int or not 1 <= cases <= 10_000:
        raise ValueError('cases must be between 1 and 10000')
    oracle = DynoOracle(executable)
    rng = random.Random(0x42D810)
    for case in range(cases):
        row = case % 20
        count = case % 40 - 2
        slots = max(1, count + 1)
        table = bytearray(row * ROW_STRIDE + ID_OFFSET + slots * ID_SLOT_STRIDE)
        ids = [rng.randrange(-32768, 32768) for _ in range(slots)]
        for index, value in enumerate(ids):
            struct.pack_into('<h', table, row * ROW_STRIDE + ID_OFFSET
                             + index * ID_SLOT_STRIDE, value)
        query = (row if case % 7 == 0 else
                 ids[rng.randrange(slots)] if count >= 0 and case % 3 == 0
                 else rng.randrange(-32768, 32768))
        expected = int(contains_track_block_id(table, count, query, row))
        oracle._reset()
        oracle.cpu.mem_write(TABLE, bytes(table))
        oracle.cpu.mem_write(0x0097c408, struct.pack('<I', TABLE))
        oracle.cpu.mem_write(0x0097dbec, struct.pack('<i', count))
        oracle.call(0x42D810, (query, row), tail=b'\xa3' + struct.pack('<I', RESULT),
                    instruction_limit=100_000)
        actual = struct.unpack('<i', oracle.cpu.mem_read(RESULT, 4))[0]
        if actual != expected:
            raise AssertionError(
                f'case {case}: count={count} row={row} query={query} expected={expected} got={actual}')
    return {'entry': '0x42d810', 'cases': cases,
            'scope': 'return values for row equality, negative count, slot hits and misses'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    parser.add_argument('--cases', type=int, default=512)
    args = parser.parse_args()
    print(json.dumps(verify(args.executable, args.cases)))


if __name__ == '__main__':
    main()
