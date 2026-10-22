"""Compare the 0x45d1f0 sampled-body prefilter with original x86 execution."""
import json
import math
import random
import struct

from unicorn import UC_HOOK_CODE

from client.body_constructor import construct_body
from client.collision_world_candidate import (decode_collision_world_sample,
                                              world_sample_overlaps_body)
from tools.native_oracle import DynoOracle


OWNER = 0x71008000
TABLE = 0x71004000
RECORD = 0x71002000


def _packed_sample(position, vertical, kind):
    image = bytearray(0x14)
    fixed = tuple(round(value * 65536.) for value in position)
    struct.pack_into('<3i', image, 0, *fixed)
    struct.pack_into('<h', image, 0x0c, vertical)
    image[0x13] = kind
    return bytes(image)


def compare(executable, count=128):
    if type(count) is not int or count < 1:
        raise ValueError('case count must be positive')
    rng = random.Random(0x45D1F0)
    oracle = DynoOracle(executable)
    cpu = oracle.cpu
    reached_classifier = False
    classifier_entries = 0

    def stub_classifier(machine, address, _size, _user):
        nonlocal reached_classifier, classifier_entries
        if address != 0x42D9F0:
            return
        reached_classifier = True
        classifier_entries += 1
        sp = machine.reg_read(oracle.reg.UC_X86_REG_ESP)
        ret = struct.unpack('<I', machine.mem_read(sp, 4))[0]
        machine.reg_write(oracle.reg.UC_X86_REG_EAX, 0)
        machine.reg_write(oracle.reg.UC_X86_REG_ESP, sp + 4)
        machine.reg_write(oracle.reg.UC_X86_REG_EIP, ret)

    cpu.hook_add(UC_HOOK_CODE, stub_classifier)
    for index in range(count):
        curated = index in (1, 2, 3, 4)
        extents = ((1., 1., 1.) if curated else
                   tuple(rng.uniform(.5, 2.) for _ in range(3)))
        yaw = 0. if curated else rng.uniform(-math.pi, math.pi)
        cosine, sine = math.cos(yaw), math.sin(yaw)
        body = bytearray(construct_body(bytearray(0x2000), OWNER, 1., extents, 0, 0))
        matrix = (cosine, 0., -sine, 0., 1., 0., sine, 0., cosine)
        struct.pack_into('<9f', body, 0x78, *matrix)
        struct.pack_into('<9f', body, 0x9c, *matrix)
        body_position = ((0., 0., 0.) if curated else
                         tuple(rng.uniform(-2., 2.) for _ in range(3)))
        body_height = (1. if index == 4 else
                       (0. if curated else rng.uniform(-.5, .5)))
        struct.pack_into('<3f', body, 8, *body_position)
        struct.pack_into('<f', body, 0x350, body_height)
        if index == 0:
            sample_position, vertical, kind = (0., 0., 0.), 256, 0
        elif index == 1:
            sample_position, vertical, kind = (0., 0., 0.), 256, 3
        elif index == 2:
            sample_position, vertical, kind = (4., 0., 0.), 256, 3
        elif index == 3:
            sample_position, vertical, kind = (2.25, 0., 0.), 256, 3
        elif index == 4:
            sample_position, vertical, kind = (0., 0., 0.), 256, 3
        else:
            sample_position = tuple(rng.uniform(-8., 8.) for _ in range(3))
            vertical = rng.randint(0, 4096)
            kind = 1 + index % 3
        sample = _packed_sample(sample_position, vertical, kind)
        decoded = decode_collision_world_sample(sample)
        expected = kind != 0 and world_sample_overlaps_body(body, decoded)

        oracle._reset()
        cpu.mem_write(OWNER, bytes(body))
        cpu.mem_write(0x0097C408, struct.pack('<I', TABLE))
        cpu.mem_write(TABLE + 0x684, struct.pack('<I', 1))
        cpu.mem_write(TABLE + 0x688, struct.pack('<I', RECORD))
        cpu.mem_write(RECORD, sample)
        reached_classifier = False
        oracle.call(0x45D1F0, (OWNER, 0), instruction_limit=1_000_000)
        if reached_classifier != expected:
            raise AssertionError(
                f'case {index}: native classifier entry {reached_classifier} '
                f'!= prefilter {expected}; sample={decoded!r}')
    return {'entry': '0x45d1f0', 'cases': count,
            'classifier_entries': classifier_entries,
            'scope': 'sample decode and strict horizontal/local-extent prefilter; 0x42d9f0 stubbed'}


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    parser.add_argument('--cases', type=int, default=128)
    args = parser.parse_args()
    print(json.dumps(compare(args.executable, args.cases)))
