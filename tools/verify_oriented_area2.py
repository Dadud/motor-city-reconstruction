"""Compare rounded 2D oriented-area determinants with native 0x6f2da0."""
import argparse
import json
import random
import struct

from client.geometry_math import rounded_oriented_area2
from tools.native_oracle import DynoOracle


POINTS = (0x71001000, 0x71001010, 0x71001020)


def verify(executable, cases=512):
    if type(cases) is not int or not 1 <= cases <= 10_000:
        raise ValueError('cases must be between 1 and 10000')
    oracle = DynoOracle(executable)
    rng = random.Random(0x6F2DA0)
    fixed = (((0., 0.), (2., 0.), (0., 3.)),
             ((0., 0.), (1., 0.), (0., 0.5)),
             ((0., 0.), (1., 0.), (0., 1.5)),
             ((0., 0.), (0., 3.), (2., 0.)))
    samples = list(fixed)
    samples.extend(tuple(tuple(rng.uniform(-1e4, 1e4) for _ in range(2))
                         for _ in range(3))
                   for _ in range(max(0, cases - len(samples))))
    for index, points in enumerate(samples):
        expected = rounded_oriented_area2(*points)
        oracle._reset()
        for address, point in zip(POINTS, points):
            oracle.cpu.mem_write(address, struct.pack('<2f', *point))
        oracle.call(0x6F2DA0, POINTS, instruction_limit=100_000)
        actual = oracle.cpu.reg_read(oracle.reg.UC_X86_REG_EAX)
        signed_actual = actual - (1 << 32) if actual & 0x80000000 else actual
        if signed_actual != expected:
            raise AssertionError(
                f'case {index}: native={signed_actual}, expected={expected}, points={points!r}')
    return {'entry': '0x6f2da0', 'cases': len(samples),
            'scope': 'signed 2D determinant and x87 nearest-even int32 rounding'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    parser.add_argument('--cases', type=int, default=512)
    args = parser.parse_args()
    print(json.dumps(verify(args.executable, args.cases)))


if __name__ == '__main__':
    main()
