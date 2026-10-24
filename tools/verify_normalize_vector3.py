"""Compare 0x6f1100 vector normalization with the installed client."""
import argparse
import math
import random
import struct
from pathlib import Path

from client.matrix_math import normalize_vector3
from tools.native_oracle import DynoOracle


def verify(executable, cases=512):
    oracle = DynoOracle(executable)
    rng = random.Random(0x6f1100)
    vectors = [(3., 0., 4.), (1., 2., 3.), (0., 0., 0.),
               (1e-20, -2e-20, 3e-20), (1e20, -2e20, 3e20)]
    vectors.extend(tuple(rng.uniform(-1e4, 1e4) for _ in range(3))
                   for _ in range(max(0, cases-len(vectors))))
    for index, vector in enumerate(vectors):
        expected = normalize_vector3(vector)
        actual = oracle.normalize_vector3(vector)
        for component, (got, want) in enumerate(zip(actual, expected)):
            if math.isnan(got) and math.isnan(want):
                continue
            if struct.pack('<f', got) != struct.pack('<f', want):
                raise AssertionError((index, vector, component, got, want))
    return len(vectors)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', type=Path)
    parser.add_argument('--cases', type=int, default=512)
    args = parser.parse_args()
    if not 5 <= args.cases <= 4096:
        parser.error('--cases must be within [5, 4096]')
    print(f'0x6f1100 matches {verify(args.executable, args.cases)} native calls exactly')
