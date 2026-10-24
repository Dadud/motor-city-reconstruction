"""Compare 0x6f1430's x87 atan2-to-turn conversion with mcity.exe."""
import argparse
import random
import struct
from pathlib import Path

from client.matrix_math import _round_binary32, atan2_turns
from tools.native_oracle import DynoOracle


def verify(executable, cases=1024):
    oracle = DynoOracle(executable)
    rng = random.Random(0x6f1430)
    vectors = [(0.0, 1.0), (1.0, 0.0), (-1.0, 0.0),
               (0.0, -1.0), (1.0, 1.0), (1.0, -1.0),
               (-1.0, -1.0), (-1.0, 1.0), (-0.0, 1.0),
               (0.0, 0.0), (-0.0, -0.0), (0.0, -0.0)]
    vectors.extend((rng.uniform(-1e6, 1e6), rng.uniform(-1e6, 1e6))
                   for _ in range(max(0, cases-len(vectors))))
    for index, (y, x) in enumerate(vectors):
        expected = _round_binary32(atan2_turns(y, x))
        actual = oracle.atan2_turns(y, x)
        if struct.pack('<f', actual) != struct.pack('<f', expected):
            raise AssertionError((index, y, x, actual, expected))
    return len(vectors)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', type=Path)
    parser.add_argument('--cases', type=int, default=1024)
    args = parser.parse_args()
    if not 1 <= args.cases <= 4096:
        parser.error('--cases must be within [1, 4096]')
    print(f'0x6f1430 atan2 turns matches {verify(args.executable, args.cases)} '
          'native float stores bit-for-bit')
