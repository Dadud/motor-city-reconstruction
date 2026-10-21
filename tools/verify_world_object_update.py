"""Compare the complete 0x520250 object update, including 22 world vertices."""
import argparse
from pathlib import Path
import struct
import subprocess

from client.world_object_update import WorldObjectUpdate, update_world_object
from client.world_object_record import update_object_record
from tools.native_oracle import DynoOracle


def verify(executable, native_runner=None):
    oracle = DynoOracle(executable)
    address = oracle.inputs
    local_vertices = tuple((i % 7 - 3) / 8 for i in range(66))
    cases = (
        ((2.0, -3.0, 1.0), (0.75, -0.25, 0.5),
         (0.03125, -0.015625, 0.0078125), (0.25, -0.5, 0.125),
         (1, 0, 0, 0, 1, 0, 0, 0, 1)),
        ((-1.0, 2.0, 0.5), (0.0, 0.0, 0.0), (0.0, 0.0, 0.0),
         (0.25, -0.5, 0.125), (0, -1, 0, 1, 0, 0, 0, 0, 1)),
        ((0.0, 0.0, 0.0), (1.0, -0.5, 0.25), (0.125, 0.0, -0.0625),
         (0.0, 0.0, 0.0), (1, 0, 0, 0, 1, 0, 0, 0, 1)),
        ((1.0, 1.0, -2.0), (-0.25, 0.5, 0.125), (0.0, 0.0, 0.0),
         (0.5, 0.25, -0.125), (0, 1, 0, -1, 0, 0, 0, 0, 1)),
    )

    def record_for(position, velocity, angular, center, rotation):
        record = bytearray(0x4f8)
        struct.pack_into('<I', record, 0, 1)
        record[4] = 1
        struct.pack_into('<3f', record, 8, *position)
        struct.pack_into('<3f', record, 0x14, *velocity)
        struct.pack_into('<3f', record, 0x38, *angular)
        struct.pack_into('<3f', record, 0x5c, *center)
        struct.pack_into('<9f', record, 0x78, *rotation)
        struct.pack_into('<3f', record, 0x328, 0.5, -0.25, 1.0)
        struct.pack_into('<66f', record, 0xe0, *local_vertices)
        return record

    checks = ((8, 12), (0x78, 36), (0x9c, 36), (0xc0, 12), (0x1e8, 264))
    for position, velocity, angular, center, rotation in cases:
        for object_phase in (0, 2):
            record = record_for(position, velocity, angular, center, rotation)
            oracle.cpu.mem_write(address, bytes(record))
            oracle.cpu.mem_write(0x00aa456c, struct.pack('<I', object_phase))
            # This executes the original 0x6f1320 wrapper and its actual
            # mode-6 vertex transformer instead of replacing the render call.
            oracle.call(0x00520250, (address,), instruction_limit=250000)
            original = bytes(oracle.cpu.mem_read(address, len(record)))
            translated_record = bytearray(record)
            update_object_record(translated_record, object_phase=object_phase)
            if original != translated_record:
                differences = [i for i, (left, right) in
                               enumerate(zip(original, translated_record))
                               if left != right]
                raise AssertionError(f'0x520250 byte-image adapter mismatch at '
                                     f'{[hex(i) for i in differences[:16]]}')
            def get(offset, count):
                return struct.unpack_from('<%df' % count, record, offset)
            state = WorldObjectUpdate(
                1, True, get(8, 3), get(0x14, 3), get(0x5c, 3), get(0x78, 9),
                get(0x38, 3), get(0x328, 3), local_vertices, (0.0,) * 66)
            updated, _ = update_world_object(state, object_phase=object_phase)
            expected = bytearray(record)
            struct.pack_into('<3f', expected, 8, *updated.position)
            struct.pack_into('<9f', expected, 0x78, *updated.rotation)
            struct.pack_into('<9f', expected, 0x9c, *updated.transposed_rotation)
            struct.pack_into('<3f', expected, 0xc0, *updated.projected)
            struct.pack_into('<66f', expected, 0x1e8, *updated.world_vertices)
            for offset, size in checks:
                if original[offset:offset+size] != expected[offset:offset+size]:
                    raise AssertionError(f'0x520250 mismatch at +0x{offset:x}: '
                                         f'{original[offset:offset+size].hex()} != '
                                         f'{expected[offset:offset+size].hex()}')
            if native_runner is not None:
                values = [1, 1, object_phase, *state.position,
                          *state.linear_velocity, *state.center_of_mass,
                          *state.rotation, *state.angular_velocity,
                          *state.projection_vectors, *state.local_vertices]
                result = subprocess.run([str(native_runner)],
                    input=' '.join(format(v, '.9g') for v in values)+'\n',
                    text=True, capture_output=True, check=True)
                actual_words = tuple(int(word, 16) for word in result.stdout.split())
                expected_words = struct.unpack('<90I', struct.pack(
                    '<90f', *updated.position, *updated.rotation,
                    *updated.transposed_rotation, *updated.projected,
                    *updated.world_vertices))
                if actual_words != expected_words:
                    raise AssertionError(f'native world-object update mismatch: '
                                         f'{actual_words!r} != {expected_words!r}')
    return len(cases) * 2


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', type=Path)
    parser.add_argument('--native-runner', type=Path)
    args = parser.parse_args()
    count = verify(args.executable, args.native_runner)
    print(f'complete object motion and vertex output matches for {count} cases')


if __name__ == '__main__':
    main()
