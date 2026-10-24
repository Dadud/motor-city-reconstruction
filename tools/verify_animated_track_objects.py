"""Verify 0x42d780 around its intercepted transform-child boundary."""
import argparse
import json
import random
import struct

from client.animated_track_objects import update_animated_track_objects
from tools.native_oracle import DynoOracle


TABLE = 0x71001000
TRANSFORM_STUB = 0x70001000


def _install_transform_stub(oracle, position):
    code = bytearray(b'\x8b\x44\x24\x10')  # output pointer is argument five
    for offset, value in zip((0, 4, 8), position):
        code.extend(b'\xc7\x00' if offset == 0 else b'\xc7\x40' + bytes([offset]))
        code.extend(struct.pack('<I', struct.unpack('<I', struct.pack('<f', value))[0]))
    code.append(0xC3)
    oracle.cpu.mem_write(TRANSFORM_STUB, bytes(code))
    displacement = TRANSFORM_STUB - (0x42D7C7 + 5)
    oracle.cpu.mem_write(0x42D7C7, b'\xE8' + struct.pack('<i', displacement))


def verify(executable, cases=512):
    if type(cases) is not int or not 1 <= cases <= 10_000:
        raise ValueError('cases must be between 1 and 10000')
    oracle = DynoOracle(executable)
    rng = random.Random(0x42D780)
    for case in range(cases):
        count = case % 8
        scale = rng.uniform(-3., 3.)
        target = tuple(rng.uniform(-500., 500.) for _ in range(3))
        records = []
        for index in range(count):
            record = bytearray(rng.getrandbits(8) for _ in range(0x78))
            struct.pack_into('<3f', record, 0,
                             *(rng.uniform(-100., 100.) for _ in range(3)))
            struct.pack_into('<I', record, 0x74,
                             0 if (case + index) % 3 == 0 else TABLE + 0x8000 + index * 0x100)
            records.append(bytes(record))
        expected = update_animated_track_objects(records, scale,
                                                  lambda index, image: target)
        oracle._reset()
        _install_transform_stub(oracle, target)
        oracle.cpu.mem_write(TABLE, b''.join(records))
        oracle.cpu.mem_write(0x0097c398, struct.pack('<i', count))
        oracle.cpu.mem_write(0x0097c410, struct.pack('<I', TABLE))
        oracle.cpu.mem_write(0x0083b7b8, struct.pack('<f', scale))
        oracle.call(0x42D780, (), instruction_limit=100_000)
        actual = bytes(oracle.cpu.mem_read(TABLE, count * 0x78))
        wanted = b''.join(expected)
        if actual != wanted:
            offset = next(i for i, (a, b) in enumerate(zip(actual, wanted)) if a != b)
            raise AssertionError(f'case {case}: byte {offset:#x}: {actual[offset]:#04x} != {wanted[offset]:#04x}')
    return {'entry': '0x42d780', 'cases': cases,
            'scope': 'full object-record writes with transform child replaced by supplied positions'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    parser.add_argument('--cases', type=int, default=512)
    args = parser.parse_args()
    print(json.dumps(verify(args.executable, args.cases)))


if __name__ == '__main__':
    main()
