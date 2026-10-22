"""Compare the 0x428680 world-data pointer layout to mcity.exe."""
import argparse
import json
import random
import struct

from client.world_dataset_layout import layout_pointer_record_section
from tools.native_oracle import DynoOracle


BASE = 0x71000000
DESCRIPTOR = BASE + 0x1000
TABLE = BASE + 0x2000
CURSOR = 0x0097C390


def compare(executable, cases=256):
    if type(cases) is not int or cases < 1:
        raise ValueError('case count must be positive')
    oracle = DynoOracle(executable)
    cpu = oracle.cpu
    rng = random.Random(0x428680)
    rows_checked = 0
    empty_sections = 0
    for case in range(cases):
        count = 0 if case % 11 == 0 else rng.randrange(1, 10)
        image = bytearray(0x10000)
        struct.pack_into('<II', image, DESCRIPTOR - BASE, count, 0xdead0000 + case)
        for index in range(count):
            row = TABLE - BASE + index * 0x38
            payload_size = 0 if (case + index) % 5 == 0 else rng.randrange(1, 17)
            vertex_count = rng.randrange(0, 9)
            triangle_count = rng.randrange(0, 8)
            struct.pack_into('<I', image, row + 0x1c, payload_size)
            struct.pack_into('<I', image, row + 0x24, vertex_count)
            struct.pack_into('<I', image, row + 0x30, triangle_count)
        initial_cursor = TABLE
        expected = bytearray(image)
        translated = layout_pointer_record_section(
            expected, BASE, DESCRIPTOR, initial_cursor)
        oracle._reset()
        cpu.mem_write(BASE, bytes(image))
        cpu.mem_write(CURSOR, struct.pack('<I', initial_cursor))
        oracle.call(0x428680, (DESCRIPTOR,), instruction_limit=500_000)
        native_image = bytes(cpu.mem_read(BASE, len(image)))
        if native_image != bytes(expected):
            for offset, (actual, wanted) in enumerate(zip(native_image, expected)):
                if actual != wanted:
                    raise AssertionError(
                        f'case {case}, byte {offset:#x}: '
                        f'native {actual:#x} != translated {wanted:#x}')
        native_cursor, = struct.unpack('<I', cpu.mem_read(CURSOR, 4))
        if native_cursor != translated['cursor_address']:
            raise AssertionError(
                f'case {case}: cursor {native_cursor:#x} != '
                f'{translated["cursor_address"]:#x}')
        rows_checked += count
        empty_sections += int(count == 0)
    return {'entry': '0x428680', 'cases': cases, 'records': rows_checked,
            'empty_sections': empty_sections, 'all_image_bytes_matched': True,
            'cursor_matched': True,
            'scope': 'original pointer-fixup routine with supplied record counts and cursor'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    parser.add_argument('--cases', type=int, default=256)
    args = parser.parse_args()
    print(json.dumps(compare(args.executable, args.cases)))
