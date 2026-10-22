"""Compare 0x4596b0's compact/full point extraction against mcity.exe."""
import argparse
import json
import random
import struct

from client.collision_world_response import extract_world_contact_points
from tools.native_oracle import DynoOracle


BODY, OUTPUT = 0x71000000, 0x71001000


def compare(executable, count=256):
    if type(count) is not int or count < 1:
        raise ValueError('case count must be positive')
    rng = random.Random(0x4596B0)
    oracle = DynoOracle(executable)
    compact_cases = 0
    full_cases = 0
    for index in range(count):
        image = bytearray(0x400)
        values = tuple(struct.unpack('<f', struct.pack('<f', rng.uniform(-1000., 1000.)))[0]
                       for _ in range(66))
        struct.pack_into('<66f', image, 0xe0, *values)
        use_compact = index % 4 in (0, 3)
        struct.pack_into('<h', image, 0x3bc, 0 if use_compact else 1)
        c4 = rng.uniform(.708, 3.) if use_compact else rng.uniform(-.706, .706)
        struct.pack_into('<f', image, 0xc4, c4)
        expected = extract_world_contact_points(image)

        cpu = oracle.cpu
        cpu.mem_write(BODY, bytes(image))
        cpu.mem_write(OUTPUT, bytes([0xcd]) * (66 * 4))
        oracle.call(0x4596B0, (BODY, OUTPUT), instruction_limit=100_000)
        returned = cpu.reg_read(oracle.reg.UC_X86_REG_EAX)
        if returned != expected.count:
            raise AssertionError(f'case {index}: count {returned} != {expected.count}')
        native = struct.unpack('<' + str(expected.count * 3) + 'f',
                               cpu.mem_read(OUTPUT, expected.count * 3 * 4))
        if native != expected.vertices:
            for offset, (actual, wanted) in enumerate(zip(native, expected.vertices)):
                if struct.pack('<f', actual) != struct.pack('<f', wanted):
                    raise AssertionError(f'case {index}: vertex float {offset}: {actual} != {wanted}')
        if expected.count == 8:
            compact_cases += 1
        else:
            full_cases += 1
    return {'entry': '0x4596b0', 'cases': count, 'compact_8_point_cases': compact_cases,
            'full_22_point_cases': full_cases,
            'scope': 'gate selection, compact coordinate construction, and full 66-float copy'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    parser.add_argument('--cases', type=int, default=256)
    args = parser.parse_args()
    print(json.dumps(compare(args.executable, args.cases)))
