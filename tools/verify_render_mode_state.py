"""Compare renderer mode cache updates at 0x6f1a30 with mcity.exe."""
import argparse
import random
from pathlib import Path

from client.render_state import replace_render_mode
from tools.native_oracle import DynoOracle


def verify(executable, cases=512):
    oracle = DynoOracle(executable)
    rng = random.Random(0x6f1a30)
    vectors = [(0, 0, 0), (0, 0xffffffff, 1),
               (0x12345678, 0x87654321, 0x20000),
               (0xffffffff, 0, 0xffffffff)]
    vectors.extend(tuple(rng.getrandbits(32) for _ in range(3))
                   for _ in range(max(0, cases-len(vectors))))
    for index, words in enumerate(vectors):
        expected = replace_render_mode(*words)
        actual = oracle.render_mode_state(*words)
        if actual != expected:
            raise AssertionError((index, words, actual, expected))
    return len(vectors)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', type=Path)
    parser.add_argument('--cases', type=int, default=512)
    args = parser.parse_args()
    if not 4 <= args.cases <= 4096:
        parser.error('--cases must be within [4, 4096]')
    print(f'0x6f1a30 render mode state matches {verify(args.executable, args.cases)} calls')
