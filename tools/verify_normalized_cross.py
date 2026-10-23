"""Compare 0x6f10d0's normalized cross product with mcity.exe."""
import argparse
import random
from pathlib import Path

from client.matrix_math import normalized_cross3
from tools.native_oracle import DynoOracle


def verify(executable, cases=512):
    oracle = DynoOracle(executable)
    rng = random.Random(0x6f10d0)
    vectors = [((1.0, 0.0, 0.0), (0.0, 1.0, 0.0)),
               ((1.0, 2.0, 3.0), (-4.0, 5.0, -6.0)),
               ((-0.25, 0.75, 0.5), (0.5, -0.25, 0.75))]
    for _ in range(max(0, cases-len(vectors))):
        left = tuple(rng.uniform(-1e3, 1e3) for _ in range(3))
        right = tuple(rng.uniform(-1e3, 1e3) for _ in range(3))
        vectors.append((left, right))
    maximum_error = 0.0
    for index, (left, right) in enumerate(vectors):
        expected = normalized_cross3(left, right)
        actual = oracle.normalized_cross3(left, right)
        for axis, (got, want) in enumerate(zip(actual, expected)):
            error = abs(got-want)
            maximum_error = max(maximum_error, error)
            if got != want:
                raise AssertionError((index, axis, left, right, got, want, error))
    return len(vectors), maximum_error


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', type=Path)
    parser.add_argument('--cases', type=int, default=512)
    args = parser.parse_args()
    if not 1 <= args.cases <= 4096:
        parser.error('--cases must be within [1, 4096]')
    count, error = verify(args.executable, args.cases)
    print(f'0x6f10d0 normalized cross product matches {count} original calls; '
          f'maximum float error {error}')
