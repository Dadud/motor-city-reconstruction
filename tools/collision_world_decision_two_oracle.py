"""Compare the 0x45d1f0 decision-2 contact-cache branch with mcity.exe."""
import argparse
import json
import random
import struct

from client.body_constructor import construct_body
from client.collision_world_candidate import decode_collision_world_sample
from client.collision_world_response import apply_world_decision_two_contact_cache
from tools.native_oracle import DynoOracle


OWNER, TABLE, RECORD = 0x71008000, 0x71004000, 0x71002000


def _sample(x, z):
    image = bytearray(0x14)
    struct.pack_into('<3i', image, 0, round(x * 65536.), 0, round(z * 65536.))
    struct.pack_into('<h', image, 0x0c, 256)
    image[0x13] = 3  # classifier decision 2, response type 0x1a
    return bytes(image)


def compare(executable, count=128):
    if type(count) is not int or count < 1:
        raise ValueError('case count must be positive')
    rng = random.Random(0x45D1F020)
    oracle = DynoOracle(executable)
    cpu = oracle.cpu
    writes = 0
    for index in range(count):
        body = bytearray(construct_body(bytearray(0x2000), OWNER, 1.,
                                        (1., 1., 1.), 0, 0))
        struct.pack_into('<3f', body, 8, 0., rng.uniform(-.5, .5), 0.)
        struct.pack_into('<f', body, 0x350, 0.)
        timer = (2., 2.0001, 3., 10.)[index % 4]
        struct.pack_into('<f', body, 0x3b4, timer)
        mass = rng.uniform(25., 2500.)
        struct.pack_into('<f', body, 0x50, mass)
        # Seed the complete contact record so the comparison also catches
        # fields which should remain untouched by the branch.
        for offset in range(0x3c4, 0x400, 4):
            struct.pack_into('<I', body, offset, rng.randrange(0x100000000))
        x, z = rng.uniform(-.6, .6), rng.uniform(-.6, .6)
        sample = _sample(x, z)
        decoded_position = decode_collision_world_sample(sample).position
        expected = apply_world_decision_two_contact_cache(
            body, 2, 0x1a, decoded_position)

        oracle._reset()
        cpu.mem_write(OWNER, bytes(body))
        cpu.mem_write(0x0097c408, struct.pack('<I', TABLE))
        cpu.mem_write(TABLE + 0x684, struct.pack('<I', 1))
        cpu.mem_write(TABLE + 0x688, struct.pack('<I', RECORD))
        cpu.mem_write(RECORD, sample)
        oracle.call(0x45D1F0, (OWNER, 0), instruction_limit=1_000_000)
        actual = bytes(cpu.mem_read(OWNER, 0x400))
        if actual != expected:
            for offset, (a, b) in enumerate(zip(actual, expected)):
                if a != b:
                    raise AssertionError(f'case {index}: body byte {offset:#x}: {a:#x} != {b:#x}')
        writes += int(timer > 2.)
    return {'entry': '0x45d1f0', 'cases': count,
            'decision_two_state_writes': writes,
            'scope': 'real kind-3 classifier and strict timer-gated contact-cache writes'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    parser.add_argument('--cases', type=int, default=128)
    args = parser.parse_args()
    print(json.dumps(compare(args.executable, args.cases)))
