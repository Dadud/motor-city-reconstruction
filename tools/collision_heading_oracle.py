"""Compare fixed-angle heading translation with original 0x6f2cc0."""
import json
import random

from client.collision_heading import heading_angle
from tools.native_oracle import DynoOracle


def compare(executable, count=4096):
    if type(count) is not int or count < 1:
        raise ValueError('case count must be positive')
    oracle = DynoOracle(executable)
    cpu = oracle.cpu
    cases = [
        (x, z)
        for x, z in ((0, 0), (0, 1), (1, 0), (0, -1), (-1, 0),
                     (1, 1), (-1, 1), (1, -1), (-1, -1),
                     (0x7fffffff, 1), (1, 0x7fffffff),
                     (-0x80000000, 1), (1, -0x80000000))
    ]
    rng = random.Random(0x6f2cc0)
    cases.extend((rng.randint(-0x80000000, 0x7fffffff),
                  rng.randint(-0x80000000, 0x7fffffff))
                 for _ in range(max(0, count - len(cases))))
    for index, (x, z) in enumerate(cases):
        oracle._reset()
        oracle.call(0x6f2cc0, (x, z))
        actual = cpu.reg_read(oracle.reg.UC_X86_REG_EAX)
        if actual & 0x80000000:
            actual -= 0x100000000
        expected = heading_angle(x, z)
        if actual != expected:
            raise AssertionError(
                f'case {index}: heading({x}, {z}) = {actual}, expected {expected}')
    return {'entry': '0x6f2cc0', 'cases': len(cases),
            'scope': 'exact 32-bit fixed-angle result including zero, axes, octants and full-range coordinates'}


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    parser.add_argument('--cases', type=int, default=4096)
    args = parser.parse_args()
    print(json.dumps(compare(args.executable, args.cases)))
