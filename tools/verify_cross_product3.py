"""Compare the unnormalized 0x6f3b75 cross product with mcity.exe."""
import argparse
import json
import random
import struct

from client.matrix_math import cross_product3
from tools.native_oracle import DynoOracle


LEFT, RIGHT, OUTPUT = 0x71001000, 0x71001020, 0x71001040


def verify(executable, cases=512):
    if type(cases) is not int or not 1 <= cases <= 10_000:
        raise ValueError('cases must be between 1 and 10000')
    oracle = DynoOracle(executable)
    rng = random.Random(0x6F3B75)
    fixed = (((1., 0., 0.), (0., 1., 0.)),
             ((1., 2., 3.), (-4., 5., -6.)),
             ((-0.25, 0.75, 0.5), (0.5, -0.25, 0.75)))
    pairs = list(fixed)
    pairs.extend((tuple(rng.uniform(-1e3, 1e3) for _ in range(3)),
                  tuple(rng.uniform(-1e3, 1e3) for _ in range(3)))
                 for _ in range(cases - len(pairs)))
    for case, (left, right) in enumerate(pairs):
        expected = cross_product3(left, right)
        oracle._reset()
        oracle.cpu.mem_write(LEFT, struct.pack('<3f', *left))
        oracle.cpu.mem_write(RIGHT, struct.pack('<3f', *right))
        oracle.cpu.mem_write(OUTPUT, bytes(12))
        oracle.call(0x6F3B75, (LEFT, RIGHT, OUTPUT), instruction_limit=100_000)
        actual = struct.unpack('<3f', oracle.cpu.mem_read(OUTPUT, 12))
        expected_words = struct.pack('<3f', *expected)
        actual_words = struct.pack('<3f', *actual)
        if actual_words != expected_words:
            raise AssertionError(
                f'case {case}: native={actual!r}, expected={expected!r}')
    return {'entry': '0x6f3b75', 'cases': len(pairs),
            'scope': 'three-component cross-product output words over explicit finite vectors'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    parser.add_argument('--cases', type=int, default=512)
    args = parser.parse_args()
    print(json.dumps(verify(args.executable, args.cases)))


if __name__ == '__main__':
    main()
