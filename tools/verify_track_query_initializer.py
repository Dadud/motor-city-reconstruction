"""Compare query-record initialization with original MCO routine 0x42d8d0."""
import argparse
import json
import random
import struct

from client.track_surface_sample import initialize_track_query_state
from tools.native_oracle import DynoOracle


RECORD = 0x71004000


def verify(executable, cases=512):
    if type(cases) is not int or not 1 <= cases <= 10_000:
        raise ValueError('cases must be between 1 and 10000')
    oracle = DynoOracle(executable)
    rng = random.Random(0x42D8D0)
    for case in range(cases):
        index = rng.randint(-0x80000000, 0x7fffffff)
        before = bytes(rng.randrange(256) for _ in range(0x44))
        expected = bytearray(before)
        initialize_track_query_state(expected, index)
        oracle._reset()
        oracle.cpu.mem_write(RECORD, before)
        oracle.call(0x42D8D0, (index, RECORD), instruction_limit=100_000)
        actual = bytes(oracle.cpu.mem_read(RECORD, 0x44))
        if actual != expected:
            offset = next(i for i, (a, b) in enumerate(zip(actual, expected)) if a != b)
            raise AssertionError(f'case {case}: byte {offset:#x}: {actual[offset]:#04x} != {expected[offset]:#04x}')
    return {'entry': '0x42d8d0', 'cases': cases,
            'scope': 'complete 0x44-byte query record, including untouched tail bytes'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    parser.add_argument('--cases', type=int, default=512)
    args = parser.parse_args()
    print(json.dumps(verify(args.executable, args.cases)))


if __name__ == '__main__':
    main()
