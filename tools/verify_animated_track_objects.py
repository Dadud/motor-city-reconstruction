"""Compare the composed 0x42d780 and 0x407940 animation path."""
import argparse
import json
import random
import struct

from client.animated_track_objects import update_animated_track_objects_from_tracks
from tools.native_oracle import DynoOracle


TABLE = 0x71001000


def _near(a, b):
    return abs(a - b) <= max(1e-5, abs(b) * 2e-6)


def verify(executable, cases=512):
    if type(cases) is not int or not 1 <= cases <= 10_000:
        raise ValueError('cases must be between 1 and 10000')
    oracle = DynoOracle(executable)
    rng = random.Random(0x42D780)
    for case in range(cases):
        count = case % 8
        scale = rng.uniform(-3., 3.)
        time_value = rng.randrange(100_001)
        records, animations = [], {}
        for index in range(count):
            record = bytearray(rng.getrandbits(8) for _ in range(0x78))
            struct.pack_into('<3f', record, 0,
                             *(rng.uniform(-100., 100.) for _ in range(3)))
            pointer = 0 if (case + index) % 3 == 0 else 0x71003000 + index * 0x200
            struct.pack_into('<I', record, 0x74, pointer)
            records.append(bytes(record))
            if pointer:
                key_count = 2 + (case + index) % 5
                interval = (0, 1, 6, 19, 401)[(case + index) % 5]
                animation = bytearray(8 + key_count * 0x14)
                struct.pack_into('<HH', animation, 4, key_count, interval)
                for frame in range(key_count):
                    offset = 8 + frame * 0x14
                    struct.pack_into('<3i', animation, offset,
                                     *(rng.randint(-500000, 500000) for _ in range(3)))
                    struct.pack_into('<4h', animation, offset + 12,
                                     *(rng.randint(-16000, 16000) for _ in range(4)))
                animations[pointer] = bytes(animation)
        expected = update_animated_track_objects_from_tracks(
            records, animations, time_value, scale)
        oracle._reset()
        oracle.cpu.mem_write(TABLE, b''.join(records))
        for pointer, animation in animations.items():
            oracle.cpu.mem_write(pointer, animation)
        oracle.cpu.mem_write(0x0097c398, struct.pack('<i', count))
        oracle.cpu.mem_write(0x0097c410, struct.pack('<I', TABLE))
        oracle.cpu.mem_write(0x0083b7b8, struct.pack('<f', scale))
        oracle.cpu.mem_write(0x00aa456c, struct.pack('<i', time_value))
        oracle.call(0x42D780, (), instruction_limit=100_000)
        actual = bytes(oracle.cpu.mem_read(TABLE, count * 0x78))
        wanted = b''.join(expected)
        for index, original in enumerate(records):
            start = index * 0x78
            native, port = actual[start:start + 0x78], wanted[start:start + 0x78]
            pointer = struct.unpack_from('<I', original, 0x74)[0]
            float_ranges = ((0, 12), (12, 48), (0x58, 0x64)) if pointer else ()
            ignored = {offset for low, high in float_ranges
                       for offset in range(low, high)}
            for offset, (a, b) in enumerate(zip(native, port)):
                if offset not in ignored and a != b:
                    raise AssertionError(
                        f'case {case}, record {index}: byte {offset:#x} differs')
            for low, high in float_ranges:
                native_values = struct.unpack_from(f'<{(high-low)//4}f', native, low)
                port_values = struct.unpack_from(f'<{(high-low)//4}f', port, low)
                for field, (a, b) in enumerate(zip(native_values, port_values)):
                    if not _near(a, b):
                        raise AssertionError(
                            f'case {case}, record {index}: float {low:#x}+{field} '
                            f'native={a} port={b}')
    return {'entry': '0x42d780', 'cases': cases,
            'scope': 'full parent and animation-child composition; float fields compared with stated tolerance'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    parser.add_argument('--cases', type=int, default=512)
    args = parser.parse_args()
    print(json.dumps(verify(args.executable, args.cases)))


if __name__ == '__main__':
    main()
