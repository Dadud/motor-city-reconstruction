"""Compare the unnormalized 0x42f0c0 track camera record writes."""
import argparse
import json
import random
import struct

from client.track_surface import build_track_camera_state
from tools.native_oracle import DynoOracle


ROWS, STATE = 0x71001000, 0x71004000
FLOAT_OFFSETS = tuple(range(0x0c, 0x40, 4))
FLOAT_BYTES = {byte for offset in FLOAT_OFFSETS for byte in range(offset, offset + 4)}


def verify(executable, cases=512):
    if type(cases) is not int or not 1 <= cases <= 10_000:
        raise ValueError('cases must be between 1 and 10000')
    oracle = DynoOracle(executable)
    rng = random.Random(0x42F0C0)
    for case in range(cases):
        track_index = case % 20
        mode = case % 3
        row = tuple(round(rng.uniform(-100., 100.) * 8) / 8 for _ in range(21))
        row = row[:12] + (rng.uniform(0., 10.), rng.uniform(0., 10.)) + row[14:]
        vertical = round(rng.uniform(-10., 10.) * 8) / 8
        initial = bytes(rng.getrandbits(8) for _ in range(0x60))
        expected = build_track_camera_state(row, track_index, mode, vertical, initial)
        row_base = ROWS + track_index * 0x54
        native_rows = bytearray((track_index + 1) * 0x54)
        struct.pack_into('<21f', native_rows, track_index * 0x54, *row)

        oracle._reset()
        oracle.cpu.mem_write(ROWS, bytes(native_rows))
        oracle.cpu.mem_write(STATE, initial)
        oracle.cpu.mem_write(0x0097C38C, struct.pack('<I', ROWS))
        oracle.cpu.mem_write(0x0098C0F8, struct.pack('<I', STATE))
        vertical_bits = struct.unpack('<I', struct.pack('<f', vertical))[0]
        oracle.call(0x42F0C0, (track_index, 0, mode, vertical_bits),
                    instruction_limit=100_000)
        actual = bytes(oracle.cpu.mem_read(STATE, len(initial)))
        if actual[0x44:0x4c] != expected[0x44:0x4c]:
            raise AssertionError(f'case {case}: index fields differ')
        for offset in range(len(initial)):
            if offset in FLOAT_OFFSETS:
                native = struct.unpack_from('<f', actual, offset)[0]
                model = struct.unpack_from('<f', expected, offset)[0]
                if abs(native - model) > max(2e-5, abs(native) * 2e-6):
                    raise AssertionError(
                        f'case {case}, offset {offset:#x}: native={native}, model={model}')
            elif (offset not in FLOAT_BYTES and not 0x44 <= offset < 0x4c and
                  actual[offset] != expected[offset]):
                raise AssertionError(f'case {case}, untouched byte {offset:#x} changed')
        dirty = struct.unpack('<I', oracle.cpu.mem_read(0x0098C0FC, 4))[0]
        if dirty != 1:
            raise AssertionError(f'case {case}: dirty flag={dirty}')
    return {'entry': '0x42f0c0', 'cases': cases,
            'scope': 'track row pose copy and forward/reverse/neutral normal offsets; optional matrix normalization excluded'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    parser.add_argument('--cases', type=int, default=512)
    args = parser.parse_args()
    print(json.dumps(verify(args.executable, args.cases)))


if __name__ == '__main__':
    main()
