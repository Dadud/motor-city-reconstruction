"""Compare actual FRD object descriptors with native 0x428680 layout."""
import argparse
import json
import struct
from pathlib import Path

from client.track_mesh import decode_mesh
from client.world_dataset_layout import layout_pointer_record_section
from tools.native_oracle import DynoOracle


BASE = 0x71000000
DESCRIPTOR = BASE + 0x1000
TABLE = BASE + 0x2000
CURSOR = 0x0097C390


def verify(executable, track_files):
    oracle = DynoOracle(executable)
    cpu = oracle.cpu
    groups_checked = objects_checked = 0
    for track_file in track_files:
        groups = []
        decode_mesh(Path(track_file).read_bytes(), materials=True,
                    object_records=groups)
        for group in groups:
            count = len(group.objects)
            image = bytearray(0x10000)
            struct.pack_into('<II', image, DESCRIPTOR - BASE, count, 0)
            records = b''.join(obj.descriptor for obj in group.objects)
            image[TABLE - BASE:TABLE - BASE + len(records)] = records
            expected = bytearray(image)
            translated = layout_pointer_record_section(
                expected, BASE, DESCRIPTOR, TABLE)
            oracle._reset()
            cpu.mem_write(BASE, bytes(image))
            cpu.mem_write(CURSOR, struct.pack('<I', TABLE))
            oracle.call(0x428680, (DESCRIPTOR,), instruction_limit=500_000)
            actual = bytes(cpu.mem_read(BASE, len(image)))
            if actual != bytes(expected):
                offset = next(i for i, (a, b) in enumerate(zip(actual, expected)) if a != b)
                raise AssertionError(
                    f'{track_file}, block {group.block_index}, section '
                    f'{group.section_offset:#x}: byte {offset:#x} differs')
            native_cursor, = struct.unpack('<I', cpu.mem_read(CURSOR, 4))
            if native_cursor != translated['cursor_address']:
                raise AssertionError(
                    f'{track_file}, block {group.block_index}: native cursor '
                    f'{native_cursor:#x} != translated {translated["cursor_address"]:#x}')
            groups_checked += 1
            objects_checked += count
    return {'entry': '0x428680', 'tracks': len(tuple(track_files)),
            'object_groups': groups_checked, 'objects': objects_checked,
            'all_native_descriptor_bytes_and_cursors_matched': True}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    parser.add_argument('tracks', nargs='+')
    args = parser.parse_args()
    print(json.dumps(verify(args.executable, args.tracks)))
