"""Compare coarse fixed-angle heading translation with original 0x6f2b90."""
import argparse
import json
import random

from client.heading_byte import heading_byte
from tools.native_oracle import DynoOracle


def verify(executable, cases=4096):
    if type(cases) is not int or not 1 <= cases <= 100_000:
        raise ValueError('cases must be between 1 and 100000')
    oracle = DynoOracle(executable)
    rng = random.Random(0x6F2B90)
    samples = [(x, y) for x, y in (
        (0, 0), (1, 0), (0, 1), (0, -1), (-1, 0), (1, 1), (-1, 1),
        (1, -1), (-1, -1), (1, 2), (2, 1), (0x7fffffff, 1),
        (1, 0x7fffffff), (-0x7fffffff, 1), (1, -0x7fffffff))]
    samples.extend((rng.randint(-0x7fffffff, 0x7fffffff),
                    rng.randint(-0x7fffffff, 0x7fffffff))
                   for _ in range(max(0, cases - len(samples))))
    for index, coordinates in enumerate(samples):
        oracle._reset()
        oracle.call(0x6F2B90, coordinates)
        actual = oracle.cpu.reg_read(oracle.reg.UC_X86_REG_EAX)
        expected = heading_byte(*coordinates) & 0xffffffff
        if actual != expected:
            raise AssertionError(
                f'case {index}: native={actual:#x}, expected={expected:#x}, '
                f'coordinates={coordinates!r}')
    return {'entry': '0x6f2b90', 'cases': len(samples),
            'scope': 'exact 1/1024-turn octant lookup and signed reflection; '
                     'INT_MIN excluded'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    parser.add_argument('--cases', type=int, default=4096)
    args = parser.parse_args()
    print(json.dumps(verify(args.executable, args.cases)))


if __name__ == '__main__':
    main()
