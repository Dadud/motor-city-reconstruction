"""Compare the 0x4954c0 fixed-step point producer with mcity.exe."""
import argparse
import json
import random

from client.matrix_math import linear_vector_sequence
from tools.native_oracle import DynoOracle


def verify(executable, cases=512):
    oracle = DynoOracle(executable)
    rng = random.Random(0x4954c0)
    maximum_error = 0.0
    for index in range(cases):
        first = tuple(rng.uniform(-1e6, 1e6) for _ in range(3))
        second = tuple(rng.uniform(-1e6, 1e6) for _ in range(3))
        count = 2 + rng.randrange(63)
        expected = linear_vector_sequence(first, second, count)
        actual = oracle.linear_vector_sequence(count, first, second)
        if len(actual) != len(expected):
            raise AssertionError((index, len(actual), len(expected)))
        for point, (got, target) in enumerate(zip(actual, expected)):
            for axis, (a, b) in enumerate(zip(got, target)):
                if a != b:
                    raise AssertionError((index, point, axis, a, b))
    return {'cases': cases, 'points_compared': 'all produced 3D points',
            'maximum_float_error': maximum_error,
            'scope': 'supplied two-point seeds; original x86 binary32 output'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    parser.add_argument('--cases', type=int, default=512)
    args = parser.parse_args()
    if not 1 <= args.cases <= 4096:
        parser.error('--cases must be within [1, 4096]')
    print(json.dumps(verify(args.executable, args.cases)))
