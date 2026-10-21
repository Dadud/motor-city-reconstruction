"""Compare the signed mouse clamp helper with original code at 0x6f1380."""
import argparse
import random
from pathlib import Path

from tools.native_oracle import DynoOracle


def signed32(value):
    return value - (1 << 32) if value & 0x80000000 else value


def verify(executable, cases=1000):
    from client.mouse_controller import clamp_i32

    oracle = DynoOracle(executable)
    rng = random.Random(0x6F1380)
    vectors = [
        (-(1 << 31), -(1 << 31), (1 << 31) - 1),
        ((1 << 31) - 1, -(1 << 31), (1 << 31) - 1),
        (4, 7, -3),
        (-3, -3, -3),
        (5, -10, 10),
    ]
    vectors.extend((rng.randrange(-(1 << 31), 1 << 31),
                    rng.randrange(-(1 << 31), 1 << 31),
                    rng.randrange(-(1 << 31), 1 << 31))
                   for _ in range(max(0, cases - len(vectors))))
    for index, (value, minimum, maximum) in enumerate(vectors):
        expected = clamp_i32(value, minimum, maximum)
        oracle.call(0x006F1380, (value, minimum, maximum),
                    instruction_limit=100)
        actual = signed32(oracle.cpu.reg_read(oracle.reg.UC_X86_REG_EAX))
        if actual != expected:
            raise AssertionError(f'case {index}: {(value, minimum, maximum)} '
                                 f'native={actual} python={expected}')
    return len(vectors)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', type=Path)
    parser.add_argument('--cases', type=int, default=1000)
    args = parser.parse_args()
    print(f'0x6f1380 signed clamp matches {verify(args.executable, args.cases)} '
          'original cases, including inverted bounds')


if __name__ == '__main__':
    main()
