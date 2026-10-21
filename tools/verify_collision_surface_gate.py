"""Compare successful 0x43bd30 surface gates with the shipped client.

The original 0x437b20 helper runs natively. The separate object-vtable method
is intercepted with selected results to cover both filter branches.
"""
import argparse
import random
import struct
from pathlib import Path

from client.collision_geometry import (collision_candidate_point,
                                       probe_collision_candidate,
                                       sample_collision_surface)
from client.track_surface_lookup import TrackSurfaceMemory, TrackSurfaceWorld
from tools.native_oracle import DynoOracle
from tools.track_surface_cases import (BASE, BLOCKS, GEOMETRY, PATH, fixture)


OWNER = 0x72002000
OBJECT = 0x72006000
VTABLE = 0x72006100
VIRTUAL_METHOD = 0x7000E000


def verify(executable, cases=96):
    from unicorn import UC_HOOK_CODE

    oracle = DynoOracle(executable)
    cpu, reg = oracle.cpu, oracle.reg
    rng = random.Random(0x43BD30)
    cpu.mem_write(0x0097C38C, struct.pack('<I', PATH))
    cpu.mem_write(0x00988E38, struct.pack('<I', 24))
    for address, value in ((0x009AAA74, 1), (0x009AAA78, 0),
                           (0x009AAA7C, 0), (0x009AAA90, 0),
                           (0x009AAA94, 0), (0x0098C218, 0),
                           (0x0097C180, 0)):
        cpu.mem_write(address, struct.pack('<I', value))
    cpu.mem_write(0x00A65BD0, struct.pack('<I', OBJECT))
    cpu.mem_write(OBJECT, struct.pack('<I', VTABLE))
    cpu.mem_write(VTABLE + 0x10, struct.pack('<I', VIRTUAL_METHOD))
    cpu.mem_write(VIRTUAL_METHOD, b'\xc3')

    samples = 0
    for case in range(cases):
        surface_flags = (1, 0, 0x0e, 0x40)[case % 4]
        normal_short = (32767, 26214, 20000)[(case // 4) % 3]
        virtual_result = 1 if case % 7 == 6 else 0
        longitudinal = struct.unpack('<f', struct.pack(
            '<f', rng.uniform(-0.9, 0.9)))[0]
        lateral = struct.unpack('<f', struct.pack(
            '<f', rng.uniform(-0.9, 0.9)))[0]
        longitudinal_word = struct.unpack('<I', struct.pack('<f', longitudinal))[0]
        lateral_word = struct.unpack('<I', struct.pack('<f', lateral))[0]
        upward_mask = 0 if normal_short < 0 else 7
        arena, root, _ = fixture(2, 0, 0, 0, upward_mask, 8, 8, case)
        quad = ((0, 0, 0), (16, 1, 0), (16, 3, 16), (0, -2, 16))
        for block in range(3):
            geometry_offset = GEOMETRY - BASE + block * 0x200
            for index, vertex in enumerate(quad):
                struct.pack_into('<3f', arena, geometry_offset + index * 12,
                                 *vertex)
            descriptor = geometry_offset + 0xc0
            struct.pack_into('<H', arena, descriptor + 4, surface_flags)
            struct.pack_into('<h', arena, descriptor + 10, normal_short)

        rows = []
        for index in range(24):
            offset = PATH - BASE + index * 0x54
            row = bytearray(arena[offset:offset + 0x54])
            struct.pack_into('<3f', row, 0, 8.0, 0.0, 8.0 + index * 0.01)
            struct.pack_into('<2f', row, 0x38, 2.0, 2.0)
            struct.pack_into('<I', row, 0x4c, 0xffffffff)
            rows.append(bytes(row))
            arena[offset:offset + 0x54] = row

        grid = root + bytes(65536 - len(root))
        cpu.mem_write(BASE, bytes(arena))
        cpu.mem_write(0x00A559D8, grid)
        cpu.mem_write(0x00A55970, struct.pack('<2f', 0, 0))
        cpu.mem_write(0x00A659D8, struct.pack('<2f', 1, 1))
        for address, value in ((0x0097C408, BLOCKS), (0x0097DBEC, 2)):
            cpu.mem_write(address, struct.pack('<I', value))
        owner = bytearray(0xE7C)
        owner[4] = 1
        cpu.mem_write(OWNER, bytes(owner))
        native_virtual = [virtual_result]
        saw_sample = []
        native_query_points = []

        def intercept(machine, address, _size, _data):
            if address == VIRTUAL_METHOD:
                stack = machine.reg_read(reg.UC_X86_REG_ESP)
                ret = struct.unpack('<I', machine.mem_read(stack, 4))[0]
                machine.reg_write(reg.UC_X86_REG_EAX, native_virtual[0])
                machine.reg_write(reg.UC_X86_REG_ESP, stack + 12)
                machine.reg_write(reg.UC_X86_REG_EIP, ret)
            elif address == 0x0042E010:
                saw_sample.append(True)
                stack = machine.reg_read(reg.UC_X86_REG_ESP)
                _, _output, point_ptr, point_index = struct.unpack(
                    '<4I', machine.mem_read(stack, 16))
                native_query_points.append((
                    point_index,
                    struct.unpack('<3f', machine.mem_read(point_ptr, 12))))

        hook = cpu.hook_add(UC_HOOK_CODE, intercept)
        try:
            oracle.call(0x0043BD30,
                        (OWNER, 0, longitudinal_word, 0, lateral_word),
                        instruction_limit=500000)
        finally:
            cpu.hook_del(hook)
        native_result = cpu.reg_read(reg.UC_X86_REG_EAX) & 0xff

        world = TrackSurfaceWorld(
            TrackSurfaceMemory(grid, bytes(arena), BASE), (0.0, 0.0),
            (1.0, 1.0), BLOCKS, PATH, 2, 24)
        def sample(point, index):
            result = sample_collision_surface(world, point, index)
            if result[0]:
                saw_sample.append(True)
                return result
            return result

        translated = probe_collision_candidate(
            bytes(owner), 0, longitudinal, lateral,
            path_rows=tuple(rows), path_count=24,
            range_start=0, range_end=0, lower_limit=0, upper_limit=0,
            clamp_indices=True, sample_surface=sample,
            surface_vcall_result=virtual_result)
        if not saw_sample:
            raise AssertionError(f'fixture {case} did not exercise a successful surface sample')
        expected_point = collision_candidate_point(
            rows, 0, longitudinal, lateral)
        if not native_query_points or any(
                index != 0 or point != expected_point
                for index, point in native_query_points):
            raise AssertionError(
                f'0x43bd30 query point mismatch case={case}: '
                f'native={native_query_points}, translated={expected_point}')
        if bool(native_result) != translated:
            raise AssertionError(
                f'0x43bd30 surface gate mismatch case={case} flags={surface_flags:#x} '
                f'normal={normal_short}/32768 vcall={virtual_result}: '
                f'native={bool(native_result)} translated={translated}')

        samples += 1
    return cases, samples


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', type=Path)
    parser.add_argument('--cases', type=int, default=96)
    args = parser.parse_args()
    cases, samples = verify(args.executable, args.cases)
    print(f'0x43bd30 accepted/rejected {cases} successful-hit cases; '
          f'{samples} executed actual surface samples and virtual filter outcomes')


if __name__ == '__main__':
    main()
