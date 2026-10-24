"""Compare 0x6f1650 axis-angle matrices against the original executable."""
import argparse
import json
import math
import random
import struct

from client.matrix_math import axis_angle_rotation_matrix
from tools.native_oracle import DynoOracle


AXIS, OUTPUT = 0x71001000, 0x71001020


def verify(executable, cases=512):
    if type(cases) is not int or not 1 <= cases <= 10_000:
        raise ValueError('cases must be between 1 and 10000')
    oracle = DynoOracle(executable)
    rng = random.Random(0x6F1650)
    fixed = (((1., 0., 0.), 0.), ((0., 1., 0.), 0.25),
             ((0., 0., 1.), -0.25), ((1., 2., 3.), 0.5),
             ((0., 0., 0.), 0.125))
    vectors = list(fixed)
    vectors.extend((tuple(rng.uniform(-10., 10.) for _ in range(3)),
                    rng.uniform(-2., 2.))
                   for _ in range(max(0, cases - len(vectors))))
    for index, (axis, turns) in enumerate(vectors):
        expected = axis_angle_rotation_matrix(axis, turns)
        oracle._reset()
        oracle.cpu.mem_write(AXIS, struct.pack('<3f', *axis))
        oracle.cpu.mem_write(OUTPUT, bytes(36))
        angle_bits = struct.unpack('<I', struct.pack('<f', turns))[0]
        oracle.call(0x6F1650, (AXIS, angle_bits, OUTPUT), instruction_limit=100_000)
        actual = struct.unpack('<9f', oracle.cpu.mem_read(OUTPUT, 36))
        for slot, (got, want) in enumerate(zip(actual, expected)):
            if math.isnan(want):
                if not math.isnan(got):
                    raise AssertionError(f'case {index}, matrix[{slot}]: expected NaN, got {got}')
            elif abs(got - want) > max(3e-7, abs(got) * 3e-7):
                raise AssertionError(
                    f'case {index}, matrix[{slot}]: native={got}, model={want}, '
                    f'axis={axis}, turns={turns}')
    return {'entry': '0x6f1650', 'cases': len(vectors),
            'scope': 'axis normalization, zero-angle identity, Rodrigues matrix, and zero-axis NaNs'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    parser.add_argument('--cases', type=int, default=512)
    args = parser.parse_args()
    print(json.dumps(verify(args.executable, args.cases)))


if __name__ == '__main__':
    main()
