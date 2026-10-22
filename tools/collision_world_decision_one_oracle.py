"""Compare the 0x45d1f0 kind-1 response path with the original client."""
import argparse
import json
import random
import struct

from client.body_constructor import construct_body
from client.collision_world_candidate import decode_collision_world_sample
from client.collision_world_response import resolve_world_decision_one_sample
from tools.native_oracle import DynoOracle


OWNER, TABLE, RECORD = 0x71008000, 0x71004000, 0x71002000


def _sample(x, vertical=512):
    image = bytearray(0x14)
    struct.pack_into('<3i', image, 0, round(x * 65536.), 0, 0)
    struct.pack_into('<h', image, 0x0c, vertical)
    image[0x13] = 1
    return bytes(image)


def _close(actual, expected, tolerance):
    return abs(actual - expected) <= max(tolerance, abs(expected) * 5e-6)


def compare(executable, count=128):
    if type(count) is not int or count < 1:
        raise ValueError('case count must be positive')
    rng = random.Random(0x45D1F010)
    oracle = DynoOracle(executable)
    cpu = oracle.cpu
    impacts = 0
    cache_writes = 0
    maximum_position_error = 0.0
    maximum_velocity_error = 0.0
    for index in range(count):
        body = bytearray(construct_body(bytearray(0x2000), OWNER, 1.,
                                        (1., 1., 1.), 0, 0))
        struct.pack_into('<3f', body, 8, 0., rng.uniform(-.3, .3), 0.)
        # Alternating approach/recede cases exercise both 0x457df0 outcomes.
        velocity = 1. if index % 2 == 0 else -1.
        struct.pack_into('<3f', body, 0x14, velocity, 0., 0.)
        struct.pack_into('<f', body, 0x350, 0.)
        struct.pack_into('<h', body, 0x3bc, 1)  # ordinary 22-point geometry
        struct.pack_into('<66f', body, 0xe0, *([1., 0., 0.] * 22))
        struct.pack_into('<66f', body, 0x1e8, *([.125, .25, .375] * 22))
        body[6] = 0  # keep the audio/callback path outside this slice
        sample = _sample(rng.uniform(.2, .6))
        decoded = decode_collision_world_sample(sample)
        expected = resolve_world_decision_one_sample(
            body, decoded.position, decoded.vertical_value, 0x1d)

        oracle._reset()
        cpu.mem_write(OWNER, bytes(body))
        cpu.mem_write(0x0097c408, struct.pack('<I', TABLE))
        cpu.mem_write(TABLE + 0x684, struct.pack('<I', 1))
        cpu.mem_write(TABLE + 0x688, struct.pack('<I', RECORD))
        cpu.mem_write(RECORD, sample)
        oracle.call(0x45D1F0, (OWNER, 0), instruction_limit=2_000_000)
        actual = bytes(cpu.mem_read(OWNER, 0x400))
        wanted = expected.body_image[:0x400]
        actual_position = struct.unpack_from('<3f', actual, 8)
        wanted_position = struct.unpack_from('<3f', wanted, 8)
        actual_velocity = struct.unpack_from('<3f', actual, 0x14)
        wanted_velocity = struct.unpack_from('<3f', wanted, 0x14)
        maximum_position_error = max(
            maximum_position_error,
            *(abs(a - b) for a, b in zip(actual_position, wanted_position)))
        maximum_velocity_error = max(
            maximum_velocity_error,
            *(abs(a - b) for a, b in zip(actual_velocity, wanted_velocity)))
        for label, values in (('position', (actual_position, wanted_position)),
                              ('velocity', (actual_velocity, wanted_velocity))):
            tolerance = 2e-6 if label == 'position' else 4e-5
            if not all(_close(a, b, tolerance) for a, b in zip(*values)):
                raise AssertionError(f'case {index}: {label} {values[0]} != {values[1]}')
        ignored = set(range(8, 0x20)) | set(range(0x38, 0x44))
        for offset, (a, b) in enumerate(zip(actual, wanted)):
            if offset not in ignored and a != b:
                raise AssertionError(f'case {index}: body byte {offset:#x}: {a:#x} != {b:#x}')
        impacts += int(expected.vertex_response.collided)
        cache_writes += int(expected.contact_cache_written)
    return {'entry': '0x45d1f0', 'cases': count, 'impacts': impacts,
            'contact_cache_writes': cache_writes,
            'maximum_absolute_position_error': maximum_position_error,
            'maximum_absolute_velocity_error': maximum_velocity_error,
            'scope': 'real kind-1 classifier, extracted point response, impulse, and post-response cache write'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    parser.add_argument('--cases', type=int, default=128)
    args = parser.parse_args()
    print(json.dumps(compare(args.executable, args.cases)))
