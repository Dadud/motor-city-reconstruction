"""Compare packed world-contact sample decoding with original 0x42db70."""
import json
import random
import struct

from client.collision_world_candidate import decode_collision_world_sample
from tools.native_oracle import DynoOracle


TABLE = 0x71004000
RECORDS = 0x71008000
POSITION = 0x71009000
VERTICAL = 0x71009010
RADIUS = 0x71009020


def compare(executable, count=256):
    if type(count) is not int or count < 1:
        raise ValueError('case count must be positive')
    rng = random.Random(0x42DB70)
    oracle = DynoOracle(executable)
    cpu = oracle.cpu
    kinds = (0, 1, 2, 3)
    for index in range(count):
        kind = kinds[index % 4]
        data = bytearray(0x14)
        packed_position = tuple(rng.randint(-0x7fffffff, 0x7fffffff)
                                for _ in range(3))
        vertical = rng.randint(-32768, 32767)
        struct.pack_into('<3i', data, 0, *packed_position)
        struct.pack_into('<h', data, 0x0c, vertical)
        data[0x13] = kind | (rng.randrange(64) << 2)
        valid = index % 5 != 0
        oracle._reset()
        cpu.mem_write(0x0097C408, struct.pack('<I', TABLE))
        cpu.mem_write(TABLE + 0x684, struct.pack('<I', int(valid)))
        cpu.mem_write(TABLE + 0x688, struct.pack('<I', RECORDS))
        cpu.mem_write(RECORDS, bytes(data))
        oracle.call(0x42DB70, (0, 0 if valid else 1,
                               POSITION, VERTICAL, RADIUS))
        result = cpu.reg_read(oracle.reg.UC_X86_REG_EAX)
        if not valid:
            if result != 0xffffffff:
                raise AssertionError(f'case {index}: invalid index returned {result:#x}')
            continue
        actual = (struct.unpack('<3f', cpu.mem_read(POSITION, 12)),
                  struct.unpack('<f', cpu.mem_read(VERTICAL, 4))[0],
                  struct.unpack('<f', cpu.mem_read(RADIUS, 4))[0])
        expected = decode_collision_world_sample(data)
        for label, values, wanted in (
                ('position', actual[0], expected.position),
                ('vertical value', (actual[1],), (expected.vertical_value,)),
                ('radius', (actual[2],), (expected.radius,))):
            if any(abs(a - b) > max(1e-6, abs(b) * 2e-7)
                   for a, b in zip(values, wanted)):
                raise AssertionError(
                    f'case {index}: {label} {values!r} != {wanted!r}')
        if result != 0:
            raise AssertionError(f'case {index}: valid index returned {result:#x}')
    return {'entry': '0x42db70', 'cases': count,
            'valid_cases': count - (count + 4) // 5,
            'scope': 'packed 16.16 coordinates, signed secondary value, type radii, and bounds'}


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    parser.add_argument('--cases', type=int, default=256)
    args = parser.parse_args()
    print(json.dumps(compare(args.executable, args.cases)))
