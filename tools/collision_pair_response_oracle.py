"""Compare the 0x458530 accumulated pair impact response to the original client."""
import argparse
import json
import math
import random
import struct

from client.collision_impulse import CollisionInertia
from client.collision_pair_response import CollisionImpactBody, resolve_pair_impulse
from tools.collision_pair_geometry_oracle import axes, f32
from tools.native_oracle import DynoOracle


OWNER, TARGET, CONTACT, NORMAL = 0x71000000, 0x71001000, 0x71002000, 0x71003000
IDENTITY = (1., 0., 0., 0., 1., 0., 0., 0., 1.)


def body_image(body):
    data = bytearray(body.contact_record)
    if len(data) < 0x408:
        data.extend(bytes(0x408 - len(data)))
    struct.pack_into('<B', data, 5, body.mode & 0xff)
    struct.pack_into('<3f', data, 8, *body.position)
    struct.pack_into('<3f', data, 0x14, *body.linear_velocity)
    struct.pack_into('<3f', data, 0x38, *body.angular_turn_velocity)
    struct.pack_into('<f', data, 0x50, body.mass)
    struct.pack_into('<f', data, 0x54, body.inertia.inverse_mass)
    struct.pack_into('<3f', data, 0x5c, *body.center_of_mass_local)
    struct.pack_into('<f', data, 0x68, body.response_coefficient)
    struct.pack_into('<f', data, 0x6c, body.gate)
    struct.pack_into('<9f', data, 0x78, *body.inertia.body_to_world)
    struct.pack_into('<9f', data, 0x9c, *body.inertia.world_to_body)
    struct.pack_into('<3f', data, 0x2fc, *body.inertia.inverse_inertia)
    struct.pack_into('<f', data, 0x3c0, body.peer_gate)
    struct.pack_into('<I', data, 0x404, body.embedded_contact_pointer & 0xffffffff)
    return bytes(data)


def run_native(oracle, owner, target, contact, normal, coefficients):
    oracle._reset()
    cpu = oracle.cpu
    cpu.mem_write(OWNER, body_image(owner))
    cpu.mem_write(TARGET, body_image(target))
    cpu.mem_write(CONTACT, struct.pack('<3f', *contact))
    cpu.mem_write(NORMAL, struct.pack('<3f', *normal))
    cpu.mem_write(0x0089c070, struct.pack('<f', coefficients[0]))
    cpu.mem_write(0x0089c074, struct.pack('<f', coefficients[1]))
    oracle.call(0x458530, (OWNER, TARGET, CONTACT, NORMAL),
                instruction_limit=1_000_000)
    returned = cpu.reg_read(oracle.reg.UC_X86_REG_EAX)
    records = (bytes(cpu.mem_read(OWNER + 0x3c4, 0x3c)),
               bytes(cpu.mem_read(TARGET + 0x3c4, 0x3c)))
    velocities = (struct.unpack('<3f', cpu.mem_read(OWNER + 0x14, 12)),
                  struct.unpack('<3f', cpu.mem_read(OWNER + 0x38, 12)),
                  struct.unpack('<3f', cpu.mem_read(TARGET + 0x14, 12)),
                  struct.unpack('<3f', cpu.mem_read(TARGET + 0x38, 12)))
    return returned, velocities, records


def cases(count=64):
    rng = random.Random(0x458530)
    for index in range(count):
        orientation_rows = ((1., 0., 0.), (0., 1., 0.), (0., 0., 1.)) if index < 8 else axes(*(rng.uniform(-math.pi, math.pi)
                                                                                       for _ in range(3)))
        orientation = tuple(value for row in orientation_rows for value in row)
        inverse = tuple(orientation_rows[col][row] for row in range(3) for col in range(3))
        mass_a = f32(rng.uniform(100, 1500))
        mass_b = f32(rng.uniform(100, 1500))
        if index < 8:
            position_a, position_b = (0., 0., 0.), (1., 0., 0.)
            contact, normal = (.5, 0., 0.), (-1., 0., 0.)
            linear_a, linear_b = (1., 0., 0.), (0., 0., 0.)
            angular_a = angular_b = (0., 0., 0.)
        else:
            position_a = tuple(f32(rng.uniform(-2, 2)) for _ in range(3))
            position_b = tuple(f32(position_a[i] + rng.uniform(-2, 2)) for i in range(3))
            contact = tuple(f32((position_a[i] + position_b[i]) * .5) for i in range(3))
            normal = tuple(f32(v) for v in orientation[0:3])
            linear_a = tuple(f32(rng.uniform(-3, 3)) for _ in range(3))
            linear_b = tuple(f32(rng.uniform(-3, 3)) for _ in range(3))
            angular_a = tuple(f32(rng.uniform(-.1, .1)) for _ in range(3))
            angular_b = tuple(f32(rng.uniform(-.1, .1)) for _ in range(3))
        inertia_a = CollisionInertia(f32(1 / mass_a),
            tuple(f32(rng.uniform(.001, .01)) for _ in range(3)), inverse, orientation)
        inertia_b = CollisionInertia(f32(1 / mass_b),
            tuple(f32(rng.uniform(.001, .01)) for _ in range(3)), inverse, orientation)
        common = {'mode': index % 4 in (1, 3), 'response_coefficient': .2,
                  'gate': .25, 'peer_gate': .5, 'contact_record': bytes([0xa5]) * 0x400}
        owner = CollisionImpactBody(OWNER, position_a, linear_a, angular_a,
                                    (0., 0., 0.), inertia_a, mass_a, **common)
        other_common = dict(common, mode=index % 4 in (2, 3))
        target = CollisionImpactBody(TARGET, position_b, linear_b, angular_b,
                                     (0., 0., 0.), inertia_b, mass_b, **other_common)
        yield owner, target, contact, normal, (f32(.45), f32(.2))


def compare(executable, count=64):
    oracle = DynoOracle(executable)
    maximum = 0.0
    collided = 0
    for index, (owner, target, point, normal, coefficients) in enumerate(cases(count)):
        native_hit, native_velocities, native_records = run_native(
            oracle, owner, target, point, normal, coefficients)
        expected = resolve_pair_impulse(owner, target, point, normal, *coefficients)
        if native_hit != int(expected.collided):
            raise AssertionError(f'case {index} impact decision differs: {native_hit} vs {expected}')
        python_velocities = (expected.owner.linear_velocity,
                             expected.owner.angular_turn_velocity,
                             expected.target.linear_velocity,
                             expected.target.angular_turn_velocity)
        for part, (actual, wanted) in enumerate(zip(native_velocities, python_velocities)):
            for axis, (a, b) in enumerate(zip(actual, wanted)):
                error = abs(a - b)
                maximum = max(maximum, error)
                if error > max(3e-5, abs(a) * 5e-6):
                    raise AssertionError(f'case {index} velocity[{part}][{axis}] differs: {a} != {b}')
        records = (expected.owner.contact_record[0x3c4:0x400],
                   expected.target.contact_record[0x3c4:0x400])
        for body_index, (actual, wanted) in enumerate(zip(native_records, records)):
            actual_ints = struct.unpack_from('<I', actual, 0)[0], struct.unpack_from('<I', actual, 32)[0], *struct.unpack_from('<II', actual, 48)
            wanted_ints = struct.unpack_from('<I', wanted, 0)[0], struct.unpack_from('<I', wanted, 32)[0], *struct.unpack_from('<II', wanted, 48)
            if actual_ints != wanted_ints:
                raise AssertionError(f'case {index} record {body_index} integer fields differ')
            actual_floats = (*struct.unpack_from('<f', actual, 4),
                             *struct.unpack_from('<3f', actual, 8),
                             *struct.unpack_from('<3f', actual, 20),
                             *struct.unpack_from('<3f', actual, 36),
                             *struct.unpack_from('<f', actual, 56))
            wanted_floats = (*struct.unpack_from('<f', wanted, 4),
                             *struct.unpack_from('<3f', wanted, 8),
                             *struct.unpack_from('<3f', wanted, 20),
                             *struct.unpack_from('<3f', wanted, 36),
                             *struct.unpack_from('<f', wanted, 56))
            for a, b in zip(actual_floats, wanted_floats):
                if abs(a - b) > max(2e-4, abs(a) * 1e-6):
                    raise AssertionError(f'case {index} record {body_index} float differs: {a} != {b}')
        collided += int(native_hit != 0)
    return {'entry': '0x458530', 'cases': count, 'impacts': collided,
            'maximum_absolute_velocity_error': maximum,
            'scope': 'sampled contact impulse accumulation and reciprocal contact record writes'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    parser.add_argument('--cases', type=int, default=64)
    args = parser.parse_args()
    print(json.dumps(compare(args.executable, args.cases)))


if __name__ == '__main__':
    main()
