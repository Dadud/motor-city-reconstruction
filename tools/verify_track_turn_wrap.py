"""Compare track turn wrapping at 0x4b70f0 with mcity.exe."""
import argparse
import random
import struct
from pathlib import Path

from client.track_cross_section import wrap_track_turn
from tools.native_oracle import DynoOracle


def verify(executable, cases=1024):
    oracle = DynoOracle(executable)
    rng = random.Random(0x4b70f0)
    values = [-100.0, -3.2, -2.0, -1.2, -1.0, -0.8, -0.2,
              -0.0, 0.0, 0.2, 1.0, 1.000001, 1.2, 2.0, 3.2, 100.0]
    values.extend(rng.uniform(-1000.0, 1000.0)
                  for _ in range(max(0, cases-len(values))))
    for index, value in enumerate(values):
        expected = wrap_track_turn(value)
        actual = oracle.wrap_track_turn(value)
        if struct.pack('<f', actual) != struct.pack('<f', expected):
            raise AssertionError((index, value, actual, expected))
    return len(values)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', type=Path)
    parser.add_argument('--cases', type=int, default=1024)
    args = parser.parse_args()
    if not 1 <= args.cases <= 4096:
        parser.error('--cases must be within [1, 4096]')
    count = verify(args.executable, args.cases)
    print(f'0x4b70f0 track turn wrap matches {count} native calls exactly')
