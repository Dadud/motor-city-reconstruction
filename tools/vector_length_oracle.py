"""Compare client.vector_length3 with the original 0x6f1210 helper."""
import argparse
import json
import math
import random

from client.matrix_math import vector_length3
from client.tire_response import f32
from tools.native_oracle import DynoOracle


def verify(executable, cases=512):
    oracle = DynoOracle(executable)
    rng = random.Random(0x6f1210)
    vectors = [(0.0, 0.0, 0.0), (3.0, 4.0, 12.0),
               (-1e10, 1e10, -1e10), (1e-20, -2e-20, 3e-20)]
    vectors.extend(tuple(rng.uniform(-1e5, 1e5) for _ in range(3))
                   for _ in range(cases-len(vectors)))
    maximum_error = 0.0
    for index, vector in enumerate(vectors):
        expected = f32(vector_length3(vector))
        actual = oracle.vector_length3(vector)
        error = abs(actual-expected)
        maximum_error = max(maximum_error, error)
        if not math.isfinite(error) or error > max(1e-6, abs(actual)*2e-7):
            raise AssertionError((index, vector, actual, expected, error))
    return {'vectors': len(vectors), 'matches': len(vectors),
            'maximum_absolute_error': maximum_error,
            'scope': 'original x86 x87 square-root result stored as binary32'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    parser.add_argument('--cases', type=int, default=512)
    args = parser.parse_args()
    if not 4 <= args.cases <= 4096:
        parser.error('--cases must be within [4, 4096]')
    print(json.dumps(verify(args.executable, args.cases)))
