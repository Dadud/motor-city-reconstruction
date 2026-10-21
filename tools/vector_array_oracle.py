"""Compare vector-array translation helper 0x6f1450 with the original."""
import argparse
import json
import random
import struct

from client.geometry_transform import add_vector_to_points
from tools.collision_pair_geometry_oracle import f32
from tools.native_oracle import DynoOracle


POINTS, VECTOR, OUTPUT = 0x71000000, 0x71002000, 0x71003000


def cases(count):
    rng = random.Random(0x6f1450)
    sizes = (0, 1, 2, 22, 47)
    for index in range(count):
        size = sizes[index % len(sizes)]
        points = tuple(f32(rng.uniform(-1e5, 1e5)) for _ in range(size * 3))
        vector = tuple(f32(rng.uniform(-1e5, 1e5)) for _ in range(3))
        yield points, vector, size, bool(index & 1)


def original(oracle, points, vector, count, in_place):
    oracle._reset()
    cpu = oracle.cpu
    cpu.mem_write(POINTS, struct.pack('<' + 'f' * len(points), *points) if points else b'')
    cpu.mem_write(VECTOR, struct.pack('<3f', *vector))
    destination = POINTS if in_place else OUTPUT
    if not in_place and points:
        cpu.mem_write(destination, bytes(len(points) * 4))
    oracle.call(0x6f1450, (count, POINTS, VECTOR, destination),
                instruction_limit=100_000)
    output = struct.unpack('<' + 'f' * len(points), cpu.mem_read(destination, len(points) * 4)) if points else ()
    unchanged = bytes(cpu.mem_read(POINTS, len(points) * 4)) == (
        struct.pack('<' + 'f' * len(points), *points) if points else b'')
    return tuple(output), unchanged


def compare(executable, count=128):
    oracle = DynoOracle(executable)
    maximum = 0.0
    for index, (points, vector, size, in_place) in enumerate(cases(count)):
        actual, unchanged = original(oracle, points, vector, size, in_place)
        expected = add_vector_to_points(points, vector, count=size)
        if actual != expected:
            raise AssertionError(f'case {index} translated values differ')
        if size != 0 and unchanged == in_place:
            raise AssertionError(f'case {index} source/destination alias behavior differs')
        if not in_place and points and bytes(oracle.cpu.mem_read(POINTS, len(points) * 4)) != struct.pack(
                '<' + 'f' * len(points), *points):
            raise AssertionError(f'case {index} out-of-place source was modified')
        for a, b in zip(actual, expected):
            maximum = max(maximum, abs(a - b))
    return {'entry': '0x6f1450', 'cases': count, 'maximum_absolute_error': maximum,
            'scope': 'float32 vector-array translation, including overlapping buffers'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    parser.add_argument('--cases', type=int, default=128)
    args = parser.parse_args()
    print(json.dumps(compare(args.executable, args.cases)))


if __name__ == '__main__':
    main()
