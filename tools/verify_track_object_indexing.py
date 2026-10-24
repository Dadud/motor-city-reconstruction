"""Compare object pose initialization and track-row selection with 0x42d5b0."""
import argparse
import json
import random
import struct

from client.track_object_indexing import assign_track_object_indices
from tools.native_oracle import DynoOracle


OBJECTS, TRACKS, ANIMATIONS = 0x71001000, 0x71002000, 0x71005000


def _near(a, b):
    return abs(a - b) <= max(1e-5, abs(b) * 2e-6)


def verify(executable, cases=512):
    if type(cases) is not int or not 1 <= cases <= 10_000:
        raise ValueError('cases must be between 1 and 10000')
    oracle = DynoOracle(executable)
    rng = random.Random(0x42D5B0)
    for case in range(cases):
        object_count = case % 7
        track_count = 1 + case % 64
        rows = []
        for index in range(track_count):
            row = bytearray(rng.getrandbits(8) for _ in range(0x54))
            x = rng.uniform(-1000., 1000.)
            z = rng.uniform(-1000., 1000.)
            if case % 11 == 0 and index in (0, 4):
                x = z = 0.0
            struct.pack_into('<3f', row, 0, x, rng.uniform(-50., 50.), z)
            rows.append(bytes(row))
        records, animations = [], {}
        for index in range(object_count):
            record = bytearray(rng.getrandbits(8) for _ in range(0x78))
            struct.pack_into('<3f', record, 0,
                             *(rng.uniform(-1000., 1000.) for _ in range(3)))
            pointer = 0 if (case + index) % 2 == 0 else ANIMATIONS + index * 0x200
            struct.pack_into('<I', record, 0x74, pointer)
            struct.pack_into('<3f', record, 0x58, 7., 8., 9.)
            records.append(bytes(record))
            if pointer:
                animation = bytearray(8 + 2 * 0x14)
                struct.pack_into('<HH', animation, 4, 2, (case % 405))
                struct.pack_into('<3i', animation, 8,
                                 *(rng.randint(-500000, 500000) for _ in range(3)))
                struct.pack_into('<4h', animation, 20,
                                 *(rng.randint(-16000, 16000) for _ in range(4)))
                struct.pack_into('<3i', animation, 28,
                                 *(rng.randint(-500000, 500000) for _ in range(3)))
                struct.pack_into('<4h', animation, 40,
                                 *(rng.randint(-16000, 16000) for _ in range(4)))
                animations[pointer] = bytes(animation)
        expected = assign_track_object_indices(records, rows, animations)
        oracle._reset()
        oracle.cpu.mem_write(OBJECTS, b''.join(records))
        oracle.cpu.mem_write(TRACKS, b''.join(rows))
        for pointer, animation in animations.items():
            oracle.cpu.mem_write(pointer, animation)
        oracle.cpu.mem_write(0x0097c398, struct.pack('<i', object_count))
        oracle.cpu.mem_write(0x0097c410, struct.pack('<I', OBJECTS))
        oracle.cpu.mem_write(0x0097c38c, struct.pack('<I', TRACKS))
        oracle.cpu.mem_write(0x00988e38, struct.pack('<i', track_count))
        oracle.call(0x42D5B0, (), instruction_limit=1_000_000)
        actual = bytes(oracle.cpu.mem_read(OBJECTS, object_count * 0x78))
        wanted = b''.join(expected)
        for index, original in enumerate(records):
            start = index * 0x78
            native, port = actual[start:start + 0x78], wanted[start:start + 0x78]
            pointer = struct.unpack_from('<I', original, 0x74)[0]
            float_ranges = ((0, 48),) if pointer else ()
            ignored = {offset for low, high in float_ranges for offset in range(low, high)}
            for offset, (a, b) in enumerate(zip(native, port)):
                if offset not in ignored and a != b:
                    raise AssertionError(
                        f'case {case}, object {index}: byte {offset:#x} differs '
                        f'(native={a:#x}, port={b:#x})')
            for low, high in float_ranges:
                native_values = struct.unpack_from('<12f', native, low)
                port_values = struct.unpack_from('<12f', port, low)
                for field, (a, b) in enumerate(zip(native_values, port_values)):
                    if not _near(a, b):
                        raise AssertionError(
                            f'case {case}, object {index}: float {field} '
                            f'native={a} port={b}')
    return {'entry': '0x42d5b0', 'cases': cases,
            'scope': 'complete object records, including native tick-zero animation, quarter-stride row selection, delta reset, and grouped row index'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    parser.add_argument('--cases', type=int, default=512)
    args = parser.parse_args()
    print(json.dumps(verify(args.executable, args.cases)))


if __name__ == '__main__':
    main()
