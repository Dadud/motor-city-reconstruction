"""Compare signed 16.16 division against the original 0x6f2c50."""
import argparse
import json
import random

from client.fixed_math import signed_ratio_16_16
from tools.native_oracle import DynoOracle


INT_MIN, INT_MAX = -(1 << 31), (1 << 31) - 1


def verify(executable, cases=512):
    if type(cases) is not int or not 1 <= cases <= 10_000:
        raise ValueError('cases must be between 1 and 10000')
    oracle = DynoOracle(executable)
    rng = random.Random(0x6F2C50)
    operands = [(INT_MIN, 1), (INT_MIN, 2), (INT_MAX, 1),
                (-1, 3), (1, -3), (-1, -3), (7, 2), (-7, 2)]
    while len(operands) < cases:
        numerator = rng.randint(INT_MIN, INT_MAX)
        denominator = rng.randint(INT_MIN, INT_MAX)
        if denominator == 0 or (numerator == INT_MIN and denominator == -1):
            continue
        operands.append((numerator, denominator))
    for index, (numerator, denominator) in enumerate(operands):
        expected = signed_ratio_16_16(numerator, denominator) & 0xffffffff
        oracle._reset()
        oracle.call(0x6F2C50,
                    (numerator & 0xffffffff, denominator & 0xffffffff),
                    instruction_limit=100_000)
        actual = oracle.cpu.reg_read(oracle.reg.UC_X86_REG_EAX)
        if actual != expected:
            raise AssertionError(
                f'case {index}: native={actual:#010x}, expected={expected:#010x}, '
                f'operands=({numerator}, {denominator})')
    return {'entry': '0x6f2c50', 'cases': len(operands),
            'scope': 'signed int32 ratio to wrapped 16.16 quotient; divide faults excluded'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    parser.add_argument('--cases', type=int, default=512)
    args = parser.parse_args()
    print(json.dumps(verify(args.executable, args.cases)))


if __name__ == '__main__':
    main()
