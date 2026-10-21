"""Compare a successful 0x43ba40 collision probe through 0x51e460."""
import argparse
import random
import struct
from pathlib import Path

from client.collision_geometry import (probe_collision_candidate,
                                       sample_collision_surface)
from client.collision_recovery import search_surface_correction
from client.track_surface_lookup import TrackSurfaceMemory, TrackSurfaceWorld
from client.track_topology import track_index_is_rejected
from client.world_object_contact import apply_contact_frame
from client.world_object_environment import EnvironmentCallbacks
from tools.native_oracle import DynoOracle
from tools.track_surface_cases import (BASE, BLOCKS, GEOMETRY, PATH, fixture)


OWNER = 0x7100C000
INTERFACE = 0x71008000
VTABLE = 0x71008100
QUERY = 0x71008200
FINAL = 0x71008300
FALLBACK = 0x71007000


def _f32(value):
    return struct.unpack('<f', struct.pack('<f', value))[0]


def verify(executable, cases=24):
    from unicorn import UC_HOOK_CODE

    oracle = DynoOracle(executable)
    cpu, reg = oracle.cpu, oracle.reg
    rng = random.Random(0x43BA4051E460)
    max_float_error = 0.0
    float_offsets = (set(range(8, 20, 4)) | set(range(0x78, 0xcc, 4))
                     | set(range(0x1e8, 0x2f0, 4))
                     | set(range(0x31c, 0x364, 4)) | {0x350, 0x3b4, 0x3b8})

    for case in range(cases):
        arena, root, _query = fixture(2, 0, 0, 0, 7, 8, 8, case * 17)
        quad = ((0.0, 0.0, 0.0), (16.0, 0.0, 0.0),
                (16.0, 0.0, 16.0), (0.0, 0.0, 16.0))
        for block in range(3):
            geometry_offset = GEOMETRY - BASE + block * 0x200
            for vertex_index, vertex in enumerate(quad):
                struct.pack_into('<3f', arena, geometry_offset + vertex_index * 12,
                                 *vertex)
            descriptor = geometry_offset + 0xC0
            struct.pack_into('<H', arena, descriptor + 4, 1)
            struct.pack_into('<h', arena, descriptor + 10, 32767)

        rows = []
        search_rows = []
        for index in range(24):
            offset = PATH - BASE + index * 0x54
            row = bytearray(arena[offset:offset + 0x54])
            struct.pack_into('<3f', row, 0, 8.0, 0.0, 8.0 + index * 0.01)
            struct.pack_into('<3f', row, 0x0C, 0.0, 1.0, 0.0)
            struct.pack_into('<3f', row, 0x18, 0.0, 0.0, 1.0)
            struct.pack_into('<3f', row, 0x24, 1.0, 0.0, 0.0)
            struct.pack_into('<3f3I', row, 0x38,
                             2.0, 2.0, 0.0, 0,
                             1 if index == 0 else 0,
                             0x80 if index == 0 else 0)
            rows.append(bytes(row))
            search_rows.append((
                struct.unpack_from('<2f', row, 0x38) +
                struct.unpack_from('<2I', row, 0x44)))
            arena[offset:offset + 0x54] = row

        grid = root + bytes(65536 - len(root))
        cpu.mem_write(BASE, bytes(arena))
        cpu.mem_write(0x00A559D8, grid)
        cpu.mem_write(0x00A55970, struct.pack('<2f', 0.0, 0.0))
        cpu.mem_write(0x00A659D8, struct.pack('<2f', 1.0, 1.0))
        globals_ = ((0x0097C408, BLOCKS), (0x0097C38C, PATH),
                    (0x00988E38, 24), (0x0097DBEC, 2),
                    (0x009AAA74, 1), (0x009AAA78, 0),
                    (0x009AAA7C, 0), (0x009AAA90, 0),
                    (0x009AAA94, 0), (0x0098C218, 0),
                    (0x0097C180, 0), (0x008E3AB8, FALLBACK),
                    (0x00A65BD0, INTERFACE))
        for address, value in globals_:
            cpu.mem_write(address, struct.pack('<I', value))
        cpu.mem_write(FALLBACK, bytes(24 * 0x1C))
        cpu.mem_write(INTERFACE, struct.pack('<I', VTABLE))
        cpu.mem_write(VTABLE + 0x10, struct.pack('<I', QUERY))
        cpu.mem_write(VTABLE + 0x14, struct.pack('<I', FINAL))
        cpu.mem_write(QUERY, b'\xb8\0\0\0\0\xc2\x08\0')
        cpu.mem_write(FINAL, b'\xb8\0\0\0\0\xc2\x08\0')
        cpu.mem_write(0x0098C470, struct.pack('<f', 0.0))

        record = bytearray(rng.randbytes(0x1C98))
        record[4] = 1
        record[6] = 0
        struct.pack_into('<I', record, 0x370, 0)
        struct.pack_into('<I', record, 0x464, 0)
        struct.pack_into('<I', record, 0xDF4, 0)
        struct.pack_into('<3f', record, 8, 8.0, 0.0, 8.0)
        struct.pack_into('<3f', record, 0x358, 8.0, 0.0, 8.0)
        struct.pack_into('<9f', record, 0x78, 1, 0, 0, 0, 1, 0, 0, 0, 1)
        struct.pack_into('<66f', record, 0xE0,
                         *(rng.uniform(-0.5, 0.5) for _ in range(66)))
        cpu.mem_write(OWNER, bytes(record))

        memory = TrackSurfaceMemory(grid, bytes(arena), BASE)
        world = TrackSurfaceWorld(memory, (0.0, 0.0), (1.0, 1.0),
                                  BLOCKS, PATH, 2, 24)
        track_rows = tuple(tuple(struct.unpack_from('<21f', row)) for row in rows)
        callbacks = EnvironmentCallbacks(
            world, lambda *_args: None, lambda _owner: None, 0.0)
        native_calls = []
        native_responses = []

        def trace(machine, address, _size, _data):
            if address == 0x0051E460:
                stack = machine.reg_read(reg.UC_X86_REG_ESP)
                _ret, owner, index, position, flags = struct.unpack(
                    '<5I', machine.mem_read(stack, 20))
                native_responses.append((
                    index, struct.unpack('<3f', machine.mem_read(position, 12)),
                    flags))
                native_calls.append(address)
            elif address in (0x0042E010, 0x0043BD30):
                native_calls.append(address)

        hook = cpu.hook_add(UC_HOOK_CODE, trace)
        try:
            oracle.call(0x0043BA40, (OWNER, 0), instruction_limit=2_000_000)
        finally:
            cpu.hook_del(hook)
        original = bytes(cpu.mem_read(OWNER, len(record)))
        if (0x0043BD30 not in native_calls or 0x0051E460 not in native_calls
                or 0x0042E010 not in native_calls):
            raise AssertionError(f'case {case} missed a probe/response: {native_calls}')

        translated = bytearray(record)
        translated_responses = []

        def probe(owner, index, longitudinal, _unused, lateral):
            return probe_collision_candidate(
                owner, index, longitudinal, lateral,
                path_rows=rows, path_count=24,
                range_start=0, range_end=0, lower_limit=0, upper_limit=0,
                clamp_indices=True, surface_vcall_result=0,
                sample_surface=lambda point, row: sample_collision_surface(
                    world, point, row),
                world_objects=(), traffic_rows=(), owner_address=OWNER)

        def respond(owner, index, longitudinal, flags):
            translated_responses.append((index, longitudinal, flags))
            apply_contact_frame(
                owner, track_rows=track_rows, track_index=index,
                query_position=(longitudinal, 0.0, 0.0), flags=flags,
                environment_callbacks=callbacks, environment_enabled=True)

        search_surface_correction(
            translated, 0, path_rows=tuple(search_rows), path_count=24, attempts=24,
            wrapped_ordering=False, wrapped_index=False,
            probe=probe, apply_response=respond,
            fallback_table=bytes(24 * 0x1C), special_probe=False,
            alternate_track_side=False, response_mode=False,
            index_is_rejected=lambda index: track_index_is_rejected(
                index, range_start=0, range_end=0,
                lower_limit=0, upper_limit=0))

        for offset in range(0, len(record), 4):
            actual_word, expected_word = original[offset:offset + 4], translated[offset:offset + 4]
            if actual_word == expected_word:
                continue
            if offset in float_offsets:
                actual_value = struct.unpack('<f', actual_word)[0]
                expected_value = struct.unpack('<f', expected_word)[0]
                error = abs(actual_value - expected_value)
                max_float_error = max(max_float_error, error)
                if error <= 2e-4:
                    continue
            raise AssertionError(
                f'case {case} response composition mismatch at {offset:#x}: '
                f'native={actual_word.hex()} python={expected_word.hex()} '
                f'calls={native_calls} native_responses={native_responses} '
                f'translated_responses={translated_responses} '
                f'first_rows={track_rows[:1]}')
    return cases, max_float_error


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', type=Path)
    parser.add_argument('--cases', type=int, default=24)
    args = parser.parse_args()
    cases, error = verify(args.executable, args.cases)
    print(f'0x43ba40 successful collision response matches {cases} original '
          f'complete owner records through 0x51e460; maximum compared float '
          f'error {error:.9g}')


if __name__ == '__main__':
    main()
