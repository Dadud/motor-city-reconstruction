"""Compare the terrain response normal at 0x459e30 with original execution."""
import argparse
import json
import random
import struct

from client.collision_terrain import terrain_response_normal
from tools.native_oracle import DynoOracle


POINTS = 0x71002000
OUTPUT = 0x71003000


def cases(count):
    yield ((0., 0., 0.), (0., 0., 10.), (10., 0., 0.))
    yield ((10., 0., 0.), (0., 0., 10.), (0., 0., 0.))
    yield ((0., 0., 0.), (1., 0., 0.), (2., 0., 0.))
    yield ((1., 2., 3.), (1., 2., 3.), (1., 2., 3.))
    yield ((0., 0., 0.), (1., 1e-7, 0.), (2., 2.0000002e-7, 1e-8))
    rng = random.Random(0x459E30)
    for _ in range(count):
        yield tuple(tuple(rng.uniform(-100., 100.) for _ in range(3))
                    for _ in range(3))


def compare(executable, count=256):
    oracle = DynoOracle(executable)
    cpu = oracle.cpu
    maximum = 0.
    checked = 0
    for points in cases(count):
        flattened = tuple(value for point in points for value in point)
        cpu.mem_write(POINTS, struct.pack('<9f', *flattened))
        cpu.mem_write(OUTPUT, b'\xa5' * 12)
        oracle.call(0x459E30, (OUTPUT, POINTS), instruction_limit=100_000)
        actual = struct.unpack('<3f', cpu.mem_read(OUTPUT, 12))
        expected = terrain_response_normal(points)
        for index, (left, right) in enumerate(zip(actual, expected)):
            error = abs(left - right)
            maximum = max(maximum, error)
            if error > max(2e-6, abs(left) * 2e-6):
                raise AssertionError(f'case {checked} normal[{index}] {left} != {right}')
        checked += 1
    return {'entry': '0x459e30', 'cases': checked,
            'maximum_absolute_error': maximum,
            'scope': 'supplied three-point response normal; original x86 execution'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    parser.add_argument('--cases', type=int, default=256)
    args = parser.parse_args()
    print(json.dumps(compare(args.executable, args.cases)))
