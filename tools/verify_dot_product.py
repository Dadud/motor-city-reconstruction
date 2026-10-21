"""Compare 0x6f1140's returned three-vector dot product against the original."""
import argparse
from pathlib import Path
import struct

from client.matrix_math import dot_3_f32
from tools.native_oracle import DynoOracle


def verify(executable):
    oracle = DynoOracle(executable)
    left, right, output = oracle.inputs, oracle.inputs + 0x20, oracle.inputs + 0x40
    cases = (
        ((1, 2, 3), (4, -5, 6)),
        ((1e20, 1, -1e20), (1, 1, 1)),
        ((-0.25, 3.5, 1.125), (8, -2, 0.5)),
        ((1e-20, -3e-20, 5e-20), (1e20, 1e20, -1e20)),
    )
    tail = b'\xd9\x1d' + struct.pack('<I', output)  # fstp dword ptr [output]
    for a, b in cases:
        oracle.cpu.mem_write(left, struct.pack('<3f', *a))
        oracle.cpu.mem_write(right, struct.pack('<3f', *b))
        oracle.cpu.mem_write(output, bytes(4))
        oracle.call(0x006f1140, arguments=(left, right), tail=tail)
        actual = bytes(oracle.cpu.mem_read(output, 4))
        expected = struct.pack('<f', dot_3_f32(a, b))
        if actual != expected:
            raise AssertionError(f'original dot product mismatch: {actual!r} != {expected!r}')
    return len(cases)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', type=Path, help='exact verified original executable')
    args = parser.parse_args()
    print(f'original dot product matches for {verify(args.executable)} cases')


if __name__ == '__main__':
    main()
