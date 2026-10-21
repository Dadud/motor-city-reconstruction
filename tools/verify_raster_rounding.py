"""Compare startup scanline ceil/floor helpers with the original executable."""
import argparse
import math
import random
import struct
import subprocess
from pathlib import Path

from client.raster_rounding import raster_ceil, raster_floor
from tools.native_oracle import DynoOracle


def f32(value):
    return struct.unpack('<f', struct.pack('<f', value))[0]


def verify(executable, native_runner=None):
    oracle = DynoOracle(executable)
    rng = random.Random(0x483F00)
    values = [-2147483648.0, -100000.0, -2.5, -1.5, -1.0, -0.75,
              -0.5, -0.25, -0.0, 0.0, 0.25, 0.5, 0.75, 1.0, 1.5,
              2.5, 100000.0, 2147483520.0]
    values.extend(f32(rng.uniform(-1_000_000, 1_000_000)) for _ in range(238))
    for case, value in enumerate(values):
        word = struct.unpack('<I', struct.pack('<f', value))[0]
        oracle.call(0x00483f00, (word,))
        original_ceil = oracle.cpu.reg_read(oracle.reg.UC_X86_REG_EAX)
        oracle.call(0x00483f30, (word,))
        original_floor = oracle.cpu.reg_read(oracle.reg.UC_X86_REG_EAX)
        original_ceil = struct.unpack('<i', struct.pack('<I', original_ceil))[0]
        original_floor = struct.unpack('<i', struct.pack('<I', original_floor))[0]
        expected = (raster_ceil(value), raster_floor(value))
        if (original_ceil, original_floor) != expected:
            raise AssertionError(f'Python mismatch case {case} ({value}): '
                                 f'{(original_ceil, original_floor)!r} != {expected!r}')
        if native_runner is not None:
            result = subprocess.run([str(native_runner)], input=f'{word:08x}\n',
                                    text=True, capture_output=True, check=True)
            native = tuple(map(int, result.stdout.split()))
            if native != expected:
                raise AssertionError(f'native mismatch case {case} ({value}): '
                                     f'{native!r} != {expected!r}')
    return len(values)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', type=Path)
    parser.add_argument('--native-runner', type=Path)
    args = parser.parse_args()
    count = verify(args.executable, args.native_runner)
    print(f'0x483f00 and 0x483f30 match for {count} finite inputs')


if __name__ == '__main__':
    main()
