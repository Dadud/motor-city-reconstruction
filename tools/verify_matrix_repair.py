"""Compare 0x5538a0's bounded ten-step matrix correction to the original."""
import argparse
from pathlib import Path
import struct
import subprocess

from client.matrix_math import repair_rotation_matrix
from tools.native_oracle import DynoOracle


def verify(executable, native_runner=None):
    oracle = DynoOracle(executable)
    base = oracle.inputs
    cases = (
        (1, 0, 0, 0, 1, 0, 0, 0, 1),
        (1.01, 0.01, 0, -0.01, 0.99, 0.02, 0, -0.02, 1.02),
        (0.8, 0.1, 0, -0.2, 0.9, 0.1, 0, -0.1, 1.1),
        (1, 0.125, -0.0625, -0.125, 1, 0.03125, 0.0625, -0.03125, 1),
    )
    for matrix in cases:
        oracle.cpu.mem_write(base, struct.pack('<9f', *matrix))
        oracle.call(0x005538a0, (base, 10))
        actual = bytes(oracle.cpu.mem_read(base, 36))
        expected = struct.pack('<9f', *repair_rotation_matrix(matrix))
        if actual != expected:
            raise AssertionError(f'original matrix repair mismatch: {actual.hex()} != {expected.hex()}')
        if native_runner is not None:
            fields = ['3', *(format(value, '.9g') for value in matrix), '10']
            result = subprocess.run([str(native_runner)], input=' '.join(fields)+'\n',
                                    text=True, capture_output=True, check=True)
            native = tuple(int(word, 16) for word in result.stdout.split())
            expected_words = struct.unpack('<9I', expected)
            if native != expected_words:
                raise AssertionError(f'native matrix repair mismatch: {native!r} != {expected_words!r}')
    return len(cases)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', type=Path)
    parser.add_argument('--native-runner', type=Path)
    args = parser.parse_args()
    print(f'original matrix repair matches for {verify(args.executable, args.native_runner)} cases')


if __name__ == '__main__':
    main()
