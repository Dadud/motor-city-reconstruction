"""Compare the 0x4956e0 track-color transform with mcity.exe."""
import argparse
import random
from pathlib import Path

from client.track_colors import blend_track_color
from tools.native_oracle import DynoOracle


def verify(executable, cases=1024):
    oracle = DynoOracle(executable)
    rng = random.Random(0x4956e0)
    vectors = [(0xff000000, 0xff000000, 2.0, False),
               (0xffffffff, 0xff000000, 2.0, False),
               (0x00102030, 0xffabcdef, 4.0, False),
               (0x12345678, 0x87654321, 3.0, True)]
    vectors.extend((rng.getrandbits(32), rng.getrandbits(32),
                    rng.uniform(1.0, 16.0), bool(rng.randrange(16) == 0))
                   for _ in range(max(0, cases-len(vectors))))
    for index, (argb, base, divisor, bypass) in enumerate(vectors):
        expected = blend_track_color(argb, base, divisor, bypass=bypass)
        actual = oracle.blend_track_color(argb, base, divisor, bypass=bypass)
        if actual != expected:
            raise AssertionError((index, hex(argb), hex(base), divisor,
                                  bypass, hex(actual), hex(expected)))
    return len(vectors)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', type=Path)
    parser.add_argument('--cases', type=int, default=1024)
    args = parser.parse_args()
    if not 1 <= args.cases <= 4096:
        parser.error('--cases must be within [1, 4096]')
    print(f'0x4956e0 track-color transform matches {verify(args.executable, args.cases)} '
          'original calls, including bypass')
