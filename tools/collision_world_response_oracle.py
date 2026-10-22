"""Compare the 0x459940 world-vertex scan and correction with mcity.exe."""
import argparse
import json
import random
import struct

from client.collision_impulse import CollisionInertia
from client.collision_pair_response import CollisionImpactBody
from client.collision_world_response import resolve_world_vertex_contact
from tools.native_oracle import DynoOracle


BODY, NORMAL, PLANE = 0x71000000, 0x71001000, 0x71002000
IDENTITY = (1., 0., 0., 0., 1., 0., 0., 0., 1.)


def _f32_arg(value):
    return struct.unpack('<I', struct.pack('<f', value))[0]


def _body_image(body, vertices):
    data = bytearray(body.contact_record)
    data.extend(bytes(max(0, 0x408 - len(data))))
    struct.pack_into('<h', data, 0x3bc, 1)  # use the 22 supplied geometry points
    struct.pack_into('<3f', data, 8, *body.position)
    struct.pack_into('<3f', data, 0x14, *body.linear_velocity)
    struct.pack_into('<3f', data, 0x38, *body.angular_turn_velocity)
    struct.pack_into('<f', data, 0x50, body.mass)
    struct.pack_into('<f', data, 0x54, body.inertia.inverse_mass)
    struct.pack_into('<3f', data, 0x5c, *body.center_of_mass_local)
    struct.pack_into('<f', data, 0x68, body.response_coefficient)
    struct.pack_into('<9f', data, 0x78, *body.inertia.body_to_world)
    struct.pack_into('<9f', data, 0x9c, *body.inertia.world_to_body)
    struct.pack_into('<66f', data, 0xe0, *vertices)
    struct.pack_into('<3f', data, 0x2fc, *body.inertia.inverse_inertia)
    struct.pack_into('<I', data, 0x404, body.embedded_contact_pointer)
    return bytes(data)


def compare(executable, count=128):
    if type(count) is not int or count < 1:
        raise ValueError('case count must be positive')
    rng = random.Random(0x459940)
    oracle = DynoOracle(executable)
    maximum_position = 0.0
    maximum_velocity = 0.0
    corrections = 0
    for index in range(count):
        axis = index % 3
        normal = tuple(1. if i == axis else 0. for i in range(3))
        plane = tuple(0. for _ in range(3))
        vertices = []
        for point in range(22):
            value = rng.uniform(-3., -.01) if point % 3 else rng.uniform(.01, 3.)
            vertices.extend(value if i == axis else rng.uniform(-2., 2.)
                            for i in range(3))
        vertices = tuple(struct.unpack('<66f', struct.pack('<66f', *vertices)))
        inertia = CollisionInertia(.001, (.001, .001, .001), IDENTITY, IDENTITY)
        velocity = tuple(-1. if i == axis else 0. for i in range(3)) if index % 2 else (0., 0., 0.)
        body = CollisionImpactBody(BODY, (0., 0., 0.), velocity,
                                   (0., 0., 0.), (0., 0., 0.), inertia,
                                   1000., response_coefficient=.2,
                                   contact_record=bytes(0x400))
        expected = resolve_world_vertex_contact(body, vertices, normal, plane,
                                                .25, .45, .2)

        cpu = oracle.cpu
        cpu.mem_write(BODY, _body_image(body, vertices))
        cpu.mem_write(NORMAL, struct.pack('<3f', *normal))
        cpu.mem_write(PLANE, struct.pack('<3f', *plane))
        oracle.call(0x459940, (BODY, NORMAL, PLANE, _f32_arg(.25),
                               _f32_arg(.45), _f32_arg(.2)),
                    instruction_limit=1_000_000)
        actual_result = cpu.reg_read(oracle.reg.UC_X86_REG_EAX)
        if actual_result != int(expected.collided):
            raise AssertionError(f'case {index}: return {actual_result} != {expected.collided}')
        actual_position = struct.unpack('<3f', cpu.mem_read(BODY + 8, 12))
        for actual, wanted in zip(actual_position, expected.body.position):
            error = abs(actual - wanted)
            maximum_position = max(maximum_position, error)
            if error > max(1e-6, abs(wanted) * 2e-7):
                raise AssertionError(f'case {index}: position {actual_position} != {expected.body.position}')
        actual_cached = struct.unpack('<66f', cpu.mem_read(BODY + 0x1e8, 0x108))
        wanted_cached = struct.unpack_from('<66f', expected.body.contact_record, 0x1e8)
        if actual_cached != wanted_cached:
            for item, (actual, wanted) in enumerate(zip(actual_cached, wanted_cached)):
                if actual != wanted:
                    raise AssertionError(f'case {index}: cached vertex float {item}: {actual} != {wanted}')
        actual_velocity = struct.unpack('<3f', cpu.mem_read(BODY + 0x14, 12))
        for actual, wanted in zip(actual_velocity, expected.body.linear_velocity):
            error = abs(actual - wanted)
            maximum_velocity = max(maximum_velocity, error)
            if error > max(3e-5, abs(wanted) * 5e-6):
                raise AssertionError(f'case {index}: velocity {actual_velocity} != {expected.body.linear_velocity}')
        actual_contact = bytes(cpu.mem_read(BODY + 0x3c4, 0x3c))
        wanted_contact = expected.body.contact_record[0x3c4:0x400]
        if actual_contact != wanted_contact:
            for offset, (actual, wanted) in enumerate(zip(actual_contact, wanted_contact)):
                if actual != wanted:
                    raise AssertionError(f'case {index}: contact record byte {offset:#x}: {actual:#x} != {wanted:#x}')
        corrections += int(expected.selected_vertex is not None and expected.penetration < 0.)
    return {'entry': '0x459940', 'cases': count, 'position_corrections': corrections,
            'maximum_absolute_position_error': maximum_position,
            'maximum_absolute_velocity_error': maximum_velocity,
            'scope': '22-point candidate selection, penetration correction, cached vertices, and delegated impulse/contact writes'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    parser.add_argument('--cases', type=int, default=128)
    args = parser.parse_args()
    print(json.dumps(compare(args.executable, args.cases)))
