"""Compare 0x6f1240's row-wise matrix scale with mcity.exe."""
import argparse
import json
import random
import struct

from client.matrix_math import scale_matrix_rows
from tools.native_oracle import DynoOracle


MATRIX, SCALE, OUTPUT = 0x71001000, 0x71001040, 0x71001060


def verify(executable, cases=512):
    if type(cases) is not int or not 1 <= cases <= 10_000:
        raise ValueError('cases must be between 1 and 10000')
    oracle = DynoOracle(executable)
    rng = random.Random(0x6F1240)
    for case in range(cases):
        matrix = tuple(rng.uniform(-1000., 1000.) for _ in range(9))
        scale = tuple(rng.uniform(-10., 10.) for _ in range(3))
        expected = scale_matrix_rows(matrix, scale)
        oracle._reset()
        oracle.cpu.mem_write(MATRIX, struct.pack('<9f', *matrix))
        oracle.cpu.mem_write(SCALE, struct.pack('<3f', *scale))
        oracle.cpu.mem_write(OUTPUT, b'\xa5' * 40)
        oracle.call(0x6F1240, (MATRIX, SCALE, OUTPUT), instruction_limit=100_000)
        actual = struct.unpack('<9I', oracle.cpu.mem_read(OUTPUT, 36))
        expected_words = struct.unpack('<9I', struct.pack('<9f', *expected))
        if actual != expected_words:
            actual_floats = struct.unpack('<9f', oracle.cpu.mem_read(OUTPUT, 36))
            raise AssertionError(
                f'case {case}: native={actual_floats!r}, expected={expected!r}')
        if bytes(oracle.cpu.mem_read(OUTPUT + 36, 4)) != b'\xa5' * 4:
            raise AssertionError(f'case {case}: wrote beyond the 9-float matrix')
    return {'entry': '0x6f1240', 'cases': cases,
            'scope': 'row-wise scaling of nine binary32 matrix elements and output-boundary guard'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    parser.add_argument('--cases', type=int, default=512)
    args = parser.parse_args()
    print(json.dumps(verify(args.executable, args.cases)))


if __name__ == '__main__':
    main()
