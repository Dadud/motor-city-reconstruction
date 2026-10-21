"""Compare the 321x241 projected-scene occupancy bounds with the original."""
import argparse
import random
import struct
import subprocess
from pathlib import Path

from client.raster_bounds import RASTER_HEIGHT, RASTER_WIDTH, occupied_raster_bounds
from tools.native_oracle import DynoOracle


def verify(executable, native_runner=None):
    oracle = DynoOracle(executable)
    bitmap_address = 0x73000000
    oracle.cpu.mem_map(bitmap_address, 0x14000)
    output_addresses = tuple(oracle.inputs+index*4 for index in range(4))
    rng = random.Random(0x483F60)
    size = RASTER_WIDTH*RASTER_HEIGHT
    cases = [bytes(size), bytes([1])*size]
    corners = bytearray(size)
    for index in (0, RASTER_WIDTH-1, (RASTER_HEIGHT-1)*RASTER_WIDTH, size-1):
        corners[index] = 1
    cases.append(bytes(corners))
    for density in (0.0001, 0.01, 0.25, 0.5):
        cases.append(bytes(1 if rng.random()<density else 0 for _ in range(size)))

    for case_index, bitmap in enumerate(cases):
        oracle.cpu.mem_write(bitmap_address, bitmap)
        for address in output_addresses:
            oracle.cpu.mem_write(address, struct.pack('<i', -0x55555555))
        oracle.call(0x00483f60, (bitmap_address, *output_addresses), instruction_limit=10_000_000)
        actual = tuple(struct.unpack('<i', oracle.cpu.mem_read(address, 4))[0]
                       for address in output_addresses)
        expected = occupied_raster_bounds(bitmap)
        if actual != expected[:4] or expected[4] != sum(bool(value) for value in bitmap):
            raise AssertionError(f'original 0x483f60 mismatch at case {case_index}: '
                                 f'{actual!r} != {expected!r}')
        if native_runner is not None:
            result = subprocess.run([str(native_runner)], input=bitmap.hex()+'\n',
                                    text=True, capture_output=True, check=True)
            native = tuple(map(int, result.stdout.split()))
            if native != expected:
                raise AssertionError(f'native mismatch at case {case_index}: '
                                     f'{native!r} != {expected!r}')
    return len(cases)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', type=Path)
    parser.add_argument('--native-runner', type=Path)
    args = parser.parse_args()
    count = verify(args.executable, args.native_runner)
    print(f'0x483f60 raster bounds/count match the original for {count} masks')


if __name__ == '__main__':
    main()
