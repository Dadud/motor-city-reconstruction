"""Compare the point-to-center lever arm helper 0x457910 with mcity.exe."""
import argparse
import json
import random
import struct

from client.collision_terrain import terrain_contact_lever_arm
from tools.native_oracle import DynoOracle


OWNER = 0x71008000
POINT = 0x7100A000
OUTPUT = 0x7100A100


def compare(executable, count=512):
    if type(count) is not int or count < 1:
        raise ValueError('case count must be a positive integer')
    oracle = DynoOracle(executable)
    cpu = oracle.cpu
    rng = random.Random(0x457910)
    maximum = 0.0
    checked = 0
    special = (
        ((0., 0., 0.), (0., 0., 0.),
         (1., 0., 0., 0., 1., 0., 0., 0., 1.), (0., 0., 0.)),
        ((12., -3., 8.), (1.5, -2., .25),
         (0., 0., 1., 0., 1., 0., -1., 0., 0.), (12., 2., 8.)),
        ((1e10, -1e10, 1e10), (.1, .2, .3),
         (1., 0., 0., 0., 1., 0., 0., 0., 1.),
         (1e10 + 1024., -1e10 - 2048., 1e10 + 4096.)),
    )
    cases = list(special)
    for _ in range(count):
        position = tuple(rng.uniform(-1e4, 1e4) for _ in range(3))
        center = tuple(rng.uniform(-5., 5.) for _ in range(3))
        # Diverse full-rank and non-orthogonal matrices exercise each product.
        matrix = tuple(rng.uniform(-2., 2.) for _ in range(9))
        point = tuple(position[i] + rng.uniform(-20., 20.) for i in range(3))
        cases.append((position, center, matrix, point))

    for position, center, matrix, point in cases:
        record = bytearray(0xA0)
        struct.pack_into('<3f', record, 8, *position)
        struct.pack_into('<3f', record, 0x5c, *center)
        struct.pack_into('<9f', record, 0x78, *matrix)
        cpu.mem_write(OWNER, bytes(record))
        cpu.mem_write(POINT, struct.pack('<3f', *point))
        cpu.mem_write(OUTPUT, b'\xa5' * 12)
        oracle.call(0x457910, (OWNER, POINT, OUTPUT), instruction_limit=100_000)
        actual = struct.unpack('<3f', cpu.mem_read(OUTPUT, 12))
        expected = terrain_contact_lever_arm(position, center, matrix, point)
        for axis, (left, right) in enumerate(zip(actual, expected)):
            error = abs(left - right)
            maximum = max(maximum, error)
            if error > max(2e-4, abs(left) * 2e-6):
                raise AssertionError(
                    f'case {checked} component {axis}: original {left} != translated {right}')
        checked += 1
    return {'entry': '0x457910', 'cases': checked,
            'maximum_absolute_error': maximum,
            'scope': 'owner position, local center of mass, supplied body basis and point; original x86 execution'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    parser.add_argument('--cases', type=int, default=512)
    args = parser.parse_args()
    print(json.dumps(compare(args.executable, args.cases)))
