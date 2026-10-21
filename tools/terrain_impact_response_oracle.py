"""Compare supplied-state terrain impulse helper 0x457550 with original code."""
import argparse
import json
import random
import struct

from client.collision_terrain import terrain_impact_response
from tools.native_oracle import DynoOracle


BODY = 0x71002000
NORMAL = 0x71003000


def cases(count):
    yield (1., 0., 0.), (0., 0., 0.), 1., (0., 1., 0.), .45, .2
    yield (1., 0., 0.), (0., 0., 0.), 1., (0., 1., 0.), 4., .5
    yield (1., 0., 0.), (0., 2., 0.), 1., (0., -1., 0.), .45, .2
    yield (0., 0., 0.), (0., 0., 0.), 1., (0., 1., 0.), .45, .2
    rng = random.Random(0x457550)
    normals = ((0., 1., 0.), (0., .8, .6), (.6, .8, 0.),
               (0., -1., 0.), (1., 0., 0.))
    for _ in range(count):
        velocity = tuple(rng.uniform(-25., 25.) for _ in range(3))
        angular = tuple(rng.uniform(-2., 2.) for _ in range(3))
        yield (velocity, angular, rng.uniform(.1, 3.),
               normals[rng.randrange(len(normals))], rng.uniform(.1, 8.),
               rng.uniform(0., 1.))


def _bits(value):
    return struct.unpack('<I', struct.pack('<f', value))[0]


def compare(executable, count=256):
    oracle = DynoOracle(executable)
    cpu = oracle.cpu
    maximum = 0.
    checked = 0
    for velocity, angular, gravity, normal, threshold, sliding in cases(count):
        image = bytearray(0x410)
        struct.pack_into('<3f', image, 0x14, *velocity)
        struct.pack_into('<3f', image, 0x38, *angular)
        struct.pack_into('<f', image, 0x50, gravity)
        struct.pack_into('<3f', image, 0x3d8, 123., 456., 789.)
        struct.pack_into('<I', image, 0x3e4, 0xA5A5A5A5)
        cpu.mem_write(BODY, bytes(image))
        cpu.mem_write(NORMAL, struct.pack('<3f', *normal))
        oracle.call(0x457550, (BODY, NORMAL, _bits(threshold), _bits(sliding)),
                    instruction_limit=20_000)
        actual_velocity = struct.unpack('<3f', cpu.mem_read(BODY + 0x14, 12))
        actual_angular = struct.unpack('<3f', cpu.mem_read(BODY + 0x38, 12))
        actual_impulse = struct.unpack('<3f', cpu.mem_read(BODY + 0x3d8, 12))
        actual_status = struct.unpack('<I', cpu.mem_read(BODY + 0x3e4, 4))[0]
        expected = terrain_impact_response(velocity, angular, gravity, normal,
                                           threshold, sliding)
        if actual_status != (expected.response_status if expected.applied else 0xA5A5A5A5):
            raise AssertionError(f'case {checked} response status differs')
        wanted_impulse = expected.tangential_impulse if expected.applied else (123.,456.,789.)
        for label, actual, wanted in (
                ('linear', actual_velocity, expected.linear_velocity),
                ('angular', actual_angular, expected.angular_turn_velocity),
                ('record', actual_impulse, wanted_impulse)):
            for index, (left, right) in enumerate(zip(actual, wanted)):
                error = abs(left-right)
                maximum = max(maximum,error)
                if error > max(3e-5,abs(left)*3e-6):
                    raise AssertionError(f'case {checked} {label}[{index}] {left} != {right}')
        checked += 1
    return {'entry': '0x457550', 'cases': checked,
            'maximum_absolute_error': maximum,
            'scope': 'supplied-state terrain response; original x86 execution'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    parser.add_argument('--cases', type=int, default=256)
    args = parser.parse_args()
    print(json.dumps(compare(args.executable, args.cases)))
