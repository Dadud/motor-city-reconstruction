"""Compare the 0x6f12a0 bit-copy transpose against the exact original."""
import argparse
from pathlib import Path
import random
import struct

from client.matrix_math import transpose_3x3_words
from tools.native_oracle import DynoOracle


def verify(executable, cases=512):
    if type(cases) is not int or not 1 <= cases <= 10_000:
        raise ValueError('cases must be between 1 and 10000')
    oracle = DynoOracle(executable)
    source, destination = oracle.inputs, oracle.inputs + 0x100
    fixed = (
        tuple(range(9)),
        (0x7fc12345, 0x80000000, 0, 0x3f800000, 0xbf800000,
         0x7f800000, 0xff800000, 1, 0xffffffff),
        (0xffffffff, 0x01234567, 0xfedcba98, 0x80000000,
         0x7f800000, 0x7fc00001, 0, 1, 0xdeadbeef),
    )
    rng = random.Random(0x6F12A0)
    vectors = list(fixed)
    vectors.extend(tuple(rng.getrandbits(32) for _ in range(9))
                   for _ in range(max(0, cases - len(vectors))))
    for values in vectors:
        source_before = struct.pack('<9I', *values)
        oracle.cpu.mem_write(source, struct.pack('<9I', *values))
        oracle.cpu.mem_write(destination, bytes(36))
        oracle.call(0x006f12a0, arguments=(source, destination))
        actual = struct.unpack('<9I', oracle.cpu.mem_read(destination, 36))
        expected = transpose_3x3_words(values)
        if actual != expected:
            raise AssertionError(f'original returned {actual!r}, expected {expected!r}')
        if bytes(oracle.cpu.mem_read(source, 36)) != source_before:
            raise AssertionError('transpose modified its input matrix')
    return len(vectors)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', type=Path, help='exact verified original executable')
    parser.add_argument('--cases', type=int, default=512)
    args = parser.parse_args()
    print(f'original 3x3 transpose matches for '
          f'{verify(args.executable, args.cases)} cases')


if __name__ == '__main__':
    main()
