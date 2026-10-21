"""Compare one-face 0x4836f0 rasterization against the original executable."""
import argparse
import random
import struct
import subprocess
from pathlib import Path

from client.raster_fill import rasterize_projected_triangle
from tools.native_oracle import DynoOracle

RASTER_BYTES = 321 * 241


def bits(value):
    return struct.unpack('<I', struct.pack('<f', value))[0]


class OneFaceOracle:
    """Plant the minimum observed owner/context/model chain for one triangle."""

    def __init__(self, executable):
        self.oracle = DynoOracle(executable)
        self.cpu = self.oracle.cpu
        self.root = self.oracle.inputs
        self.owner = self.root + 0x1000
        self.context = self.root + 0x2000
        self.node = self.root + 0x3000
        self.model = self.root + 0x4000
        self.bitmap = 0x73000000
        self.cpu.mem_map(self.bitmap, 0x20000)

    def write_u16(self, address, value):
        self.cpu.mem_write(address, struct.pack('<H', value))

    def write_u32(self, address, value):
        self.cpu.mem_write(address, struct.pack('<I', value & 0xffffffff))

    def write_f32(self, address, value):
        self.cpu.mem_write(address, struct.pack('<f', value))

    def rasterize(self, points, bounds):
        x_min, x_max, y_min, y_max = bounds
        self.write_u32(self.owner + 0x490, self.context)
        self.write_u32(self.context + 0x21c, self.node)
        self.write_u32(self.node, 0)
        self.write_u32(self.node + 4, self.model)
        self.write_u16(self.node + 12, 0)
        self.write_u32(self.node + 20, 0)

        self.write_u32(self.model + 0x14, 0x2000)
        self.write_u32(self.model + 0x1c, 0)
        self.write_u32(self.model + 0x420, 0)
        self.write_u32(self.model + 0x620, 0)
        self.write_u32(self.model + 0x720, 1)
        for index in range(3):
            self.write_u32(self.model + 0x203c + index * 4, index)
        for index, (x, y) in enumerate(points):
            self.write_f32(self.model + 0x4038 + index * 12, x)
            self.write_f32(self.model + 0x403c + index * 12, y)
            self.write_f32(self.model + 0x4040 + index * 12, 0.0)
        for index in range(3):
            self.write_f32(self.model + 0x120 + index * 4, 0.0)

        self.cpu.mem_write(self.bitmap, bytes(RASTER_BYTES))
        args = (self.owner, self.bitmap, *(bits(value) for value in bounds))
        self.oracle.call(0x004836f0, args, instruction_limit=5_000_000)
        return bytes(self.cpu.mem_read(self.bitmap, RASTER_BYTES))


def make_cases():
    cases = [
        (((1, 1), (9, 1), (5, 9)), (0, 10, 0, 10)),
        (((5, 9), (9, 1), (1, 1)), (0, 10, 0, 10)),
        (((2, 8), (8, 8), (5, 2)), (0, 10, 0, 10)),
        (((2, 2), (8, 2), (5, 8)), (0, 10, 0, 10)),
        (((5, 2), (5, 8), (5, 5)), (0, 10, 0, 10)),
        (((-2, 3), (7, 5), (4, 12)), (0, 10, 0, 10)),
        (((-3, -2), (3, 4), (8, -1)), (0, 10, 0, 10)),
        (((-2, 5), (4, 5), (12, 5)), (0, 10, 0, 10)),
        (((-2, 4), (-1, 7), (-3, 9)), (0, 10, 0, 10)),
        (((3.125, 1.25), (8.75, 4.5), (2.5, 9.75)), (0, 10, 0, 10)),
    ]
    rng = random.Random(0x4836F0)
    for _ in range(32):
        points = tuple((rng.uniform(-4, 14), rng.uniform(-4, 14))
                       for _ in range(3))
        cases.append((points, (0, 10, 0, 10)))
    return cases


def verify(executable, native_runner=None):
    oracle = OneFaceOracle(executable)
    cases = make_cases()
    native_input = []
    for index, (points, bounds) in enumerate(cases):
        original = oracle.rasterize(points, bounds)
        expected = rasterize_projected_triangle(points, bounds[:2], bounds[2:])
        if original != expected:
            differing = next(i for i, pair in enumerate(zip(original, expected))
                             if pair[0] != pair[1])
            raise AssertionError(
                f'Python mask mismatch at case {index}, pixel '
                f'({differing % 321}, {differing // 321}); '
                f'points={points!r}, bounds={bounds!r}')
        words = tuple(bits(value) for point in points for value in point) + \
                tuple(bits(value) for value in bounds)
        native_input.append(' '.join(f'{word:08x}' for word in words))
    if native_runner is not None:
        result = subprocess.run([str(native_runner)], input='\n'.join(native_input)+'\n',
                                text=True, capture_output=True, check=True)
        native_masks = result.stdout.splitlines()
        if len(native_masks) != len(cases):
            raise AssertionError(f'native runner returned {len(native_masks)} masks; '
                                 f'expected {len(cases)}')
        for index, (native, (points, bounds)) in enumerate(zip(native_masks, cases)):
            expected = rasterize_projected_triangle(points, bounds[:2], bounds[2:]).hex()
            if native != expected:
                raise AssertionError(f'native mask mismatch at case {index}')
    return len(cases)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', type=Path)
    parser.add_argument('--native-runner', type=Path)
    args = parser.parse_args()
    count = verify(args.executable, args.native_runner)
    print(f'one-face 0x4836f0 masks match for {count} synthetic triangles')


if __name__ == '__main__':
    main()
