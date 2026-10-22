"""Compare the swept pose and complete supplied-track 0x45c3e0 path to mcity.exe."""
import argparse
import json
import math
import random
import struct

from client.body_constructor import construct_body
from client.collision_pair_dispatch import dispatch_track_pairs, swept_pose
from client.track_surface_lookup import (TrackSurfaceMemory,
                                         TrackSurfaceWorld)
from tools.native_oracle import DynoOracle
from tools.track_surface_cases import BASE, BLOCKS, GEOMETRY, PATH, fixture


OWNER = 0x71008000
LINEAR = 0x71002000
ANGULAR = 0x71002010
POSITION = 0x71002020
MATRIX = 0x71002030
CENTER = 0x71002060


def _bits(value):
    return struct.unpack('<I', struct.pack('<f', value))[0]


def _close(actual, expected, tolerance=3e-5):
    return abs(actual - expected) <= max(tolerance, abs(expected) * 3e-6)


def _world_and_body(case):
    arena, root, seed = fixture(2, 1, 1, 0, 7, 16, 8, case & 0xff)
    for block in range(3):
        geometry = GEOMETRY + block * 0x200
        vertices = ((block * 16., 0., 0.), (block * 16. + 16., 0., 0.),
                    (block * 16. + 16., 0., 16.), (block * 16., 0., 16.))
        for index, vertex in enumerate(vertices):
            struct.pack_into('<3f', arena, geometry - BASE + index * 12, *vertex)
        descriptor = geometry + 0xc0 - BASE
        struct.pack_into('<4B', arena, descriptor, 1, 1, 1, 1)
        arena[descriptor + 4] = 1
    seed = bytearray(seed)
    struct.pack_into('<III', seed, 0, 0, 1, 0)
    struct.pack_into('<I', seed, 12, GEOMETRY + 0x200 + 0xc0)
    for index in range(4):
        struct.pack_into('<I', seed, 16 + index * 4,
                         GEOMETRY + 0x200 + index * 12)
    world = TrackSurfaceWorld(
        TrackSurfaceMemory(root + bytes(65536 - len(root)), bytes(arena), BASE),
        (0., 0.), (1., 1.), BLOCKS, PATH, 2, 24)
    image = bytearray(construct_body(bytes(0x2000), OWNER, 800. + case * 17.,
                                     (1., 1., 1.), 0, 2))
    owner_position = (17. + (case % 5 - 2) * .1,
                      .4 + (case % 4) * .05, 6. + (case % 9))
    local_point = (16. - owner_position[0], -owner_position[1], 0.)
    struct.pack_into('<3f', image, 8, *owner_position)
    struct.pack_into('<3f', image, 0x14, -24. - (case % 9) * 2.,
                     (case % 3 - 1) * .2, 0.)
    struct.pack_into('<3f', image, 0x38, 0., 0., 0.)
    struct.pack_into('<3f', image, 0x5c, 0., 0., 0.)
    struct.pack_into('<9f', image, 0x78, 1., 0., 0., 0., 1., 0., 0., 0., 1.)
    struct.pack_into('<66f', image, 0xe0, *(local_point * 22))
    struct.pack_into('<66f', image, 0x1e8, *(((16., 0., owner_position[2]) * 22)))
    struct.pack_into('<f', image, 0x318, .5 + (case % 7) * .15)
    struct.pack_into('<I', image, 0x354, case % 3)
    struct.pack_into('<I', image, 0x374, 1)
    image[0x370:0x370 + 0x44] = seed
    image[0x400] = 0x80
    return bytes(arena), root, world, bytes(image)


def _install_world(oracle, arena, root):
    cpu = oracle.cpu
    cpu.mem_write(BASE, arena)
    cpu.mem_write(0xa559d8, root + bytes(65536 - len(root)))
    cpu.mem_write(0xa55970, struct.pack('<2f', 0., 0.))
    cpu.mem_write(0xa659d8, struct.pack('<2f', 1., 1.))
    for address, value in ((0x97c408, BLOCKS), (0x97c38c, PATH),
                           (0x988e38, 24), (0x97dbec, 2)):
        cpu.mem_write(address, struct.pack('<I', value))


def compare_swept_pose(executable, count=64):
    oracle = DynoOracle(executable)
    cpu = oracle.cpu
    rng = random.Random(0x520110)
    maximum = 0.
    for case in range(count):
        image = bytearray(0x200)
        position = tuple(rng.uniform(-30., 30.) for _ in range(3))
        linear = tuple(rng.uniform(-90., 90.) for _ in range(3))
        angular = tuple(rng.uniform(-.8, .8) for _ in range(3))
        center = tuple(rng.uniform(-2., 2.) for _ in range(3))
        struct.pack_into('<3f', image, 8, *position)
        struct.pack_into('<3f', image, 0x14, *linear)
        struct.pack_into('<3f', image, 0x38, *angular)
        struct.pack_into('<3f', image, 0x5c, *center)
        struct.pack_into('<9f', image, 0x78, 1., 0., 0., 0., 1., 0., 0., 0., 1.)
        expected_position, expected_matrix = swept_pose(image)
        oracle._reset()
        cpu.mem_write(LINEAR, struct.pack('<3f', *linear))
        cpu.mem_write(ANGULAR, struct.pack('<3f', *angular))
        cpu.mem_write(POSITION, struct.pack('<3f', *position))
        cpu.mem_write(MATRIX, struct.pack('<9f', 1., 0., 0., 0., 1., 0., 0., 0., 1.))
        cpu.mem_write(CENTER, struct.pack('<3f', *center))
        oracle.call(0x520110, (_bits(1. / 32.), LINEAR, ANGULAR,
                               POSITION, MATRIX, CENTER),
                    instruction_limit=200_000)
        actual_position = struct.unpack('<3f', cpu.mem_read(POSITION, 12))
        actual_matrix = struct.unpack('<9f', cpu.mem_read(MATRIX, 36))
        for label, actual, expected in (('position', actual_position, expected_position),
                                        ('matrix', actual_matrix, expected_matrix)):
            for component, (a, b) in enumerate(zip(actual, expected)):
                maximum = max(maximum, abs(a - b))
                if not _close(a, b):
                    raise AssertionError(f'pose {case} {label}[{component}] {a} != {b}')
    return maximum


def compare_dispatch(executable, count=16):
    oracle = DynoOracle(executable)
    cpu = oracle.cpu
    impacts = 0
    maximum = 0.
    float_ranges = ((8, 0x14), (0x14, 0x20), (0x38, 0x44),
                    (0x1e8, 0x2f0), (0x3c8, 0x3e4), (0x3e8, 0x3f4))
    float_bytes = {offset for start, end in float_ranges
                   for offset in range(start, end)}
    for case in range(count):
        arena, root, world, image = _world_and_body(case)
        expected = dispatch_track_pairs(image, world)
        oracle._reset()
        _install_world(oracle, arena, root)
        cpu.mem_write(OWNER, image)
        oracle.call(0x45c3e0, (OWNER,), instruction_limit=5_000_000)
        actual = bytes(cpu.mem_read(OWNER, 0x408))
        if struct.unpack_from('<I', actual, 0x3f4)[0] != \
                struct.unpack_from('<I', expected.body_image, 0x3f4)[0]:
            raise AssertionError(f'dispatch {case}: response tag differs')
        if struct.unpack_from('<I', actual, 0x3f8)[0] != \
                struct.unpack_from('<I', expected.body_image, 0x3f8)[0]:
            raise AssertionError(f'dispatch {case}: material tier differs')
        for offset in range(0x408):
            if offset not in float_bytes and actual[offset] != expected.body_image[offset]:
                raise AssertionError(f'dispatch {case}: byte {offset:#x} differs')
        for start, end in float_ranges:
            for offset in range(start, end, 4):
                a = struct.unpack_from('<f', actual, offset)[0]
                b = struct.unpack_from('<f', expected.body_image, offset)[0]
                if math.isnan(a) and math.isnan(b):
                    continue
                error = abs(a - b)
                maximum = max(maximum, error)
                if not _close(a, b, 3e-5):
                    raise AssertionError(f'dispatch {case}: float {offset:#x}: {a} != {b}')
        impacts += int(struct.unpack_from('<I', actual, 0x3f4)[0] == 3)
    return impacts, maximum


def compare(executable, cases=16):
    pose_error = compare_swept_pose(executable, max(32, cases * 2))
    impacts, dispatch_error = compare_dispatch(executable, cases)
    return {'swept_pose_cases': max(32, cases * 2),
            'dispatcher_cases': cases,
            'dispatcher_impacts': impacts,
            'maximum_pose_error': pose_error,
            'maximum_dispatch_float_error': dispatch_error,
            'scope': 'controlled original-instruction execution with supplied track fixture; no live game runtime'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    parser.add_argument('--cases', type=int, default=16)
    args = parser.parse_args()
    print(json.dumps(compare(args.executable, args.cases)))


if __name__ == '__main__':
    main()
