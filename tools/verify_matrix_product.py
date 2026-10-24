"""Compare the alias-safe 0x6f2a60 matrix product with mcity.exe."""
import argparse
import json
import random
import struct

from client.matrix_math import multiply_3x3
from tools.native_oracle import DynoOracle


LEFT, RIGHT, OUTPUT = 0x71001000, 0x71001040, 0x71001080
GUARD = 0x710010a4


def verify(executable, cases=512):
    if type(cases) is not int or not 1 <= cases <= 10_000:
        raise ValueError('cases must be between 1 and 10000')
    oracle = DynoOracle(executable)
    rng = random.Random(0x6F2A60)
    for case in range(cases):
        left = tuple(rng.uniform(-100., 100.) for _ in range(9))
        right = tuple(rng.uniform(-100., 100.) for _ in range(9))
        for alias in ('separate', 'left', 'right', 'same-input'):
            oracle._reset()
            if alias == 'left':
                left_ptr, right_ptr, out_ptr = LEFT, RIGHT, LEFT
            elif alias == 'right':
                left_ptr, right_ptr, out_ptr = LEFT, RIGHT, RIGHT
            elif alias == 'same-input':
                left_ptr = right_ptr = out_ptr = LEFT
            else:
                left_ptr, right_ptr, out_ptr = LEFT, RIGHT, OUTPUT
            oracle.cpu.mem_write(LEFT, struct.pack('<9f', *left))
            oracle.cpu.mem_write(RIGHT, struct.pack('<9f', *right))
            if alias == 'separate':
                oracle.cpu.mem_write(out_ptr, bytes(36))
            expected = multiply_3x3(left, left if alias == 'same-input' else right)
            oracle.cpu.mem_write(GUARD, b'\x9c' * 4)
            oracle.call(0x6F2A60, (left_ptr, right_ptr, out_ptr),
                        instruction_limit=100_000)
            actual_words = struct.unpack('<9I', oracle.cpu.mem_read(out_ptr, 36))
            expected_words = struct.unpack('<9I', struct.pack('<9f', *expected))
            if actual_words != expected_words:
                actual = struct.unpack('<9f', oracle.cpu.mem_read(out_ptr, 36))
                raise AssertionError(
                    f'case {case}, alias={alias}: native={actual!r}, expected={expected!r}')
            if bytes(oracle.cpu.mem_read(GUARD, 4)) != b'\x9c' * 4:
                raise AssertionError(f'case {case}, alias={alias}: output exceeded 36 bytes')
    return {'entry': '0x6f2a60', 'cases': cases, 'native_calls': cases * 4,
            'scope': 'row-major product with separate, left, right, and identical inputs/output'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    parser.add_argument('--cases', type=int, default=512)
    args = parser.parse_args()
    print(json.dumps(verify(args.executable, args.cases)))


if __name__ == '__main__':
    main()
