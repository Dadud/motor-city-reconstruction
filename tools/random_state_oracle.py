"""Compare the explicit six-word generator with original mcity.exe."""
import argparse
import json
import random

from client.random_state import RandomState
from tools.native_oracle import DynoOracle


def verify(executable, cases=1024):
    oracle = DynoOracle(executable)
    seeds = [(0xf22d0e56, 0x883126e9, 0xc624dd2f,
              0x0702c49c, 0x9e353f7d, 0x6fdf3b64)]
    rng = random.Random(0x6f0fa0)
    seeds.extend(tuple(rng.getrandbits(32) for _ in range(6)) for _ in range(cases - 1))
    for index, initial in enumerate(seeds):
        expected_state = RandomState(initial)
        actual_return, actual_state = oracle.random_next(initial)
        expected_return = expected_state.next_u32()
        if (actual_return != expected_return or actual_state != expected_state.words):
            raise AssertionError((index, initial, actual_return, expected_return,
                                  actual_state, expected_state.words))
    return {'cases': len(seeds), 'matches': len(seeds),
            'scope': 'one transition per supplied six-word state; installed original x86 under Unicorn'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    parser.add_argument('--cases', type=int, default=1024)
    args = parser.parse_args()
    if not 1 <= args.cases <= 4096:
        parser.error('--cases must be within [1, 4096]')
    print(json.dumps(verify(args.executable, args.cases)))
