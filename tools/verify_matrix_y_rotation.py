"""Compare 0x6f1850 row rotation with the original executable."""
import argparse
import json
import random
import struct

from client.matrix_math import rotate_matrix_rows_y
from tools.native_oracle import DynoOracle


MATRIX, OUTPUT = 0x71001000, 0x71001040


def verify(executable, cases=512):
    if type(cases) is not int or not 1 <= cases <= 10_000:
        raise ValueError('cases must be between 1 and 10000')
    oracle = DynoOracle(executable)
    rng = random.Random(0x6F1850)
    for case in range(cases):
        matrix = tuple(rng.uniform(-1e3, 1e3) for _ in range(9))
        turns = (0., 0.25, -0.25, 0.5)[case % 4] if case < 16 else rng.uniform(-4., 4.)
        expected = rotate_matrix_rows_y(matrix, turns)
        for alias in (False, True):
            source = MATRIX
            output = source if alias else OUTPUT
            oracle._reset()
            oracle.cpu.mem_write(source, struct.pack('<9f', *matrix))
            if not alias:
                oracle.cpu.mem_write(output, bytes(36))
            turn_bits = struct.unpack('<I', struct.pack('<f', turns))[0]
            oracle.call(0x6F1850, (source, turn_bits, output),
                        instruction_limit=100_000)
            actual_words = struct.unpack('<9I', oracle.cpu.mem_read(output, 36))
            expected_words = struct.unpack('<9I', struct.pack('<9f', *expected))
            if actual_words != expected_words:
                actual = struct.unpack('<9f', oracle.cpu.mem_read(output, 36))
                raise AssertionError(
                    f'case {case}, alias={alias}: native={actual!r}, expected={expected!r}')
    return {'entry': '0x6f1850', 'cases': cases, 'native_calls': cases * 2,
            'scope': 'Y-axis row rotation, including in-place and separate output buffers'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    parser.add_argument('--cases', type=int, default=512)
    args = parser.parse_args()
    print(json.dumps(verify(args.executable, args.cases)))


if __name__ == '__main__':
    main()
