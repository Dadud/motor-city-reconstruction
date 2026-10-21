"""Compare supplied-world 0x459150 support correction with the original."""
import argparse
import json
import struct

from client.collision_impulse import CollisionInertia
from client.collision_pair_response import CollisionImpactBody
from client.collision_support import correct_support_geometry, resolve_support_contacts
from client.track_surface_lookup import (TrackSurfaceMemory, TrackSurfaceWorld,
                                         track_surface_lookup)
from tools.collision_pair_response_oracle import body_image
from tools.native_oracle import DynoOracle
from tools.track_surface_cases import BASE, BLOCKS, GEOMETRY, PATH, fixture


OWNER = 0x71008000
IDENTITY = (1., 0., 0., 0., 1., 0., 0., 0., 1.)
SURFACE_COEFFICIENTS = ((.45, .2),) * 32


def cases(count):
    for index in range(count):
        position_y = (-1.2, -.9, -.5, 0., .5)[index % 5]
        velocity_y = (-3., -1., 0., 1.)[(index // 5) % 4]
        x, z = ((8., 8.), (0., 0.), (16., 16.), (20., 8.))[index % 4]
        local_points = [0., 2., 0.] * 22
        local_points[:3] = (0., -.1, 0.)
        # The caller's source record is copied for each candidate. Its cache
        # fields vary here to exercise both cached and spatial-query branches.
        arena, root, seed = fixture(2, index % 2, index % 3, index % 2,
                                    7, int(x), int(z), index & 0xff)
        if index % 2:
            seed = bytearray(seed)
            struct.pack_into('<I', seed, 12, 0)
            track_surface_lookup(_make_world(arena, root),
                                 (x, position_y - .1, z), seed)
            seed = bytes(seed)
        yield index, (x, position_y, z), velocity_y, tuple(local_points), arena, root, seed


def _make_world(arena, root):
    return TrackSurfaceWorld(
        TrackSurfaceMemory(root + bytes(65536 - len(root)), bytes(arena), BASE),
        (0., 0.), (1., 1.), BLOCKS, PATH, 2, 24)


def _make_body(position, velocity_y, local_points, seed):
    inertia = CollisionInertia(1., (1., 1., 1.), IDENTITY, IDENTITY)
    body = CollisionImpactBody(OWNER, position, (0., velocity_y, 0.),
                               (0., 0., 0.), (0., 0., 0.), inertia, 1.,
                               response_coefficient=0.,
                               contact_record=bytes(0x400))
    image = bytearray(body_image(body))
    image.extend(bytes(0xa00 - len(image)))
    struct.pack_into('<66f', image, 0xe0, *local_points)
    struct.pack_into('<f', image, 0x318, 1.)
    struct.pack_into('<I', image, 0x354, 0)
    image[0x370:0x370 + 0x44] = seed[:0x44]
    relative = tuple(local_points)
    world_points = tuple(position[axis] + relative[i + axis]
                         for i in range(0, 66, 3) for axis in range(3))
    struct.pack_into('<66f', image, 0x1e8, *world_points)
    return body, image


def _install_world(oracle, arena, root):
    cpu = oracle.cpu
    cpu.mem_write(BASE, bytes(arena))
    cpu.mem_write(0xa559d8, root + bytes(65536 - len(root)))
    cpu.mem_write(0xa55970, struct.pack('<2f', 0., 0.))
    cpu.mem_write(0xa659d8, struct.pack('<2f', 1., 1.))
    for address, value in ((0x97c408, BLOCKS), (0x97c38c, PATH),
                           (0x988e38, 24), (0x97dbec, 2)):
        cpu.mem_write(address, struct.pack('<I', value))
    # The support caller indexes two adjacent 32-float coefficient tables.
    cpu.mem_write(0x89c0a8, struct.pack('<64f', *sum(([.45, .2] for _ in range(32)), [])))


def _compare(executable, count):
    oracle = DynoOracle(executable)
    maximum = 0.
    corrected = impacted = 0
    for index, position, velocity_y, local_points, arena, root, seed in cases(count):
        world = _make_world(arena, root)
        body, image = _make_body(position, velocity_y, local_points, seed)
        geometry = correct_support_geometry(world, position, IDENTITY, local_points,
                                            (seed,) * 22, velocity_y)
        expected = resolve_support_contacts(world, body, geometry,
                                            SURFACE_COEFFICIENTS, 1., 0)

        oracle._reset()
        _install_world(oracle, arena, root)
        cpu = oracle.cpu
        cpu.mem_write(OWNER, bytes(image))
        oracle.call(0x459150, (OWNER,), instruction_limit=5_000_000)
        actual_count = cpu.reg_read(oracle.reg.UC_X86_REG_EAX)
        actual_position = struct.unpack('<3f', cpu.mem_read(OWNER + 8, 12))
        actual_linear = struct.unpack('<3f', cpu.mem_read(OWNER + 0x14, 12))
        actual_angular = struct.unpack('<3f', cpu.mem_read(OWNER + 0x38, 12))
        actual_points = struct.unpack('<66f', cpu.mem_read(OWNER + 0x1e8, 264))
        if actual_count != expected.support_count:
            raise AssertionError(f'case {index} support count {actual_count} != {expected.support_count}')
        expected_record = expected.body.contact_record[0x3c4:0x400]
        actual_record = bytes(cpu.mem_read(OWNER + 0x3c4, 0x3c))
        integer_offsets = (0, 32, 48, 52)
        for offset in integer_offsets:
            a = struct.unpack_from('<I', actual_record, offset)[0]
            b = struct.unpack_from('<I', expected_record, offset)[0]
            if a != b:
                raise AssertionError(f'case {index} contact integer at {offset:#x}: {a:#x} != {b:#x}')

        fields = [('position', actual_position, expected.body.position),
                  ('linear velocity', actual_linear, expected.body.linear_velocity),
                  ('angular velocity', actual_angular, expected.body.angular_turn_velocity),
                  ('world support points', actual_points, geometry.world_points and
                   tuple(v for point in geometry.world_points for v in point))]
        for label, actual, wanted in fields:
            for component, (a, b) in enumerate(zip(actual, wanted)):
                error = abs(a - b)
                maximum = max(maximum, error)
                if error > max(4e-4, abs(b) * 2e-5):
                    raise AssertionError(f'case {index} {label}[{component}] {a} != {b}')
        for offset in (4, 8, 12, 16, 20, 24, 28, 36, 40, 44, 56):
            a = struct.unpack_from('<f', actual_record, offset)[0]
            b = struct.unpack_from('<f', expected_record, offset)[0]
            error = abs(a - b)
            maximum = max(maximum, error)
            if error > max(4e-4, abs(b) * 2e-5):
                raise AssertionError(f'case {index} contact float at {offset:#x}: {a} != {b}')
        corrected += any(abs(a - b) > 1e-6 for a, b in zip(position, geometry.position))
        impacted += actual_count != 0
    return {'entry': '0x459150', 'cases': count, 'corrected_cases': corrected,
            'impacted_cases': impacted, 'maximum_absolute_error': maximum,
            'scope': 'synthetic supplied-world support correction and impulse caller'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    parser.add_argument('--cases', type=int, default=32)
    args = parser.parse_args()
    print(json.dumps(_compare(args.executable, args.cases)))


if __name__ == '__main__':
    main()
