"""Compare the failed-lookup branch of 0x51e940 through correction search.

The original 0x43ba40 search and 0x43bd30 early collision-mask gate execute;
translated search orchestration runs against the same bounded path rows. The
stateful 0x43b750 reset remains an explicit intercepted boundary.
"""
import argparse
import random
import struct
from pathlib import Path

from client.collision_geometry import (probe_collision_candidate,
                                       sample_collision_surface)
from client.collision_recovery import search_surface_correction
from client.track_surface_lookup import TrackSurfaceMemory, TrackSurfaceWorld
from client.track_topology import track_index_is_rejected
from client.world_object_environment import EnvironmentCallbacks, environment_step
from tools.track_surface_cases import BASE, BLOCKS, PATH, fixture
from tools.native_oracle import DynoOracle


OWNER = 0x7100C000
OWNER_SIZE = 0x1C98


def verify(executable, cases=128):
    from unicorn import UC_HOOK_CODE

    oracle = DynoOracle(executable)
    cpu, reg = oracle.cpu, oracle.reg
    rng = random.Random(0x51E94043BFD0)

    for case in range(cases):
        previous = case % 24
        x = 8.0 + rng.uniform(-0.2, 0.2)
        z = 8.0 + rng.uniform(-0.2, 0.2)
        arena, root, query = fixture(
            1, 0, previous, case % 2, 7, int(x), int(z), case * 31)
        # The search walks every track row, then makes one terminal fallback
        # probe. Empty masks keep the unresolved response child out of scope.
        for index in range(24):
            offset = PATH - BASE + index * 0x54
            struct.pack_into('<2f2II', arena, offset + 0x38,
                             2.0, 2.0, 0, 0, 0)
        grid = root + bytes(65536 - len(root))
        cpu.mem_write(BASE, bytes(arena))
        cpu.mem_write(0x00A559D8, grid)
        cpu.mem_write(0x00A55970, struct.pack('<2f', 0.0, 0.0))
        cpu.mem_write(0x00A659D8, struct.pack('<2f', 1.0, 1.0))
        for address, value in ((0x0097C408, BLOCKS), (0x0097C38C, PATH),
                               (0x00988E38, 24), (0x0097DBEC, 2),
                               (0x009AAA60, 1), (0x009AAA74, 1),
                               (0x009AAA78, 0), (0x009AAA7C, 0),
                               (0x009AAA90, 0), (0x009AAA94, 0),
                               (0x0098C218, 0), (0x0097C180, 0),
                               (0x008E3AB8, 0x71007000),
                               (0x00A65BD0, 0x71008000)):
            cpu.mem_write(address, struct.pack('<I', value))
        fallback_table = bytes(24 * 0x1c)
        cpu.mem_write(0x71007000, fallback_table)
        cpu.mem_write(0x71008000, struct.pack('<I', 0x71008100))
        cpu.mem_write(0x71008100 + 0x10, struct.pack('<I', 0x71009000))
        cpu.mem_write(0x71009000, b'\xb8\0\0\0\0\xc2\x08\0')

        record = bytearray(rng.randbytes(OWNER_SIZE))
        record[4] = 1
        record[6] = 1  # 0x51e940 selects 0x43bfd0 after lookup failure.
        struct.pack_into('<I', record, 0x464, 0)
        struct.pack_into('<3f', record, 8, x, rng.uniform(-2.0, 8.0), z)
        struct.pack_into('<3f', record, 0x358, x, rng.uniform(-2.0, 8.0), z)
        struct.pack_into('<3f', record, 0x14,
                         *(rng.uniform(-1.0, 1.0) for _ in range(3)))
        struct.pack_into('<9f', record, 0x78, 1, 0, 0, 0, 1, 0, 0, 0, 1)
        struct.pack_into('<66f', record, 0xE0,
                         *(rng.uniform(-1.0, 1.0) for _ in range(66)))
        record[0x370:0x370 + 68] = query
        struct.pack_into('<I', record, 0x370, previous)
        struct.pack_into('<I', record, 0x378, 1)
        struct.pack_into('<3f', record, 0x370 + 44, 0.0, 1.0, 0.0)
        status = (0, 1, -1, 17)[case % 4]
        struct.pack_into('<i', record, 0x36C, status)
        cpu.mem_write(OWNER, bytes(record))

        step = rng.uniform(-20.0, 20.0)
        cpu.mem_write(0x0098C470, struct.pack('<f', step))
        mode_active = bool(case & 1)
        mode_number = case % 2
        cpu.mem_write(0x00AA459C, struct.pack('<B', int(mode_active)))
        cpu.mem_write(0x00A6CC40, struct.pack('<I', mode_number))

        native_calls = []

        def intercept_correction_children(machine, address, _size, _data):
            if address in (0x0043BFD0, 0x0043BA40, 0x0043BD30):
                native_calls.append(address)
            elif address == 0x0043B750:
                native_calls.append(address)
                stack = machine.reg_read(reg.UC_X86_REG_ESP)
                return_address = struct.unpack('<I', machine.mem_read(stack, 4))[0]
                machine.reg_write(reg.UC_X86_REG_ESP, stack + 4)
                machine.reg_write(reg.UC_X86_REG_EIP, return_address)

        hook = cpu.hook_add(UC_HOOK_CODE, intercept_correction_children)
        try:
            oracle.call(0x0051E940, (OWNER,), instruction_limit=1_000_000)
        finally:
            cpu.hook_del(hook)
        original = bytes(cpu.mem_read(OWNER, OWNER_SIZE))
        if native_calls != [0x0043BFD0, 0x0043BA40,
                            0x0043BD30, 0x0043B750]:
            raise AssertionError(
                f'case {case} failed lookup did not traverse the expected '
                f'correction chain: {[hex(address) for address in native_calls]}')

        memory = TrackSurfaceMemory(grid, bytes(arena), BASE)
        world = TrackSurfaceWorld(memory, (0.0, 0.0), (1.0, 1.0),
                                  BLOCKS, PATH, 2, 24)
        path_rows = tuple(bytes(arena[PATH - BASE + index * 0x54:
                                      PATH - BASE + (index + 1) * 0x54])
                          for index in range(24))

        def adjust_contact(owner, track_index):
            def probe(image, index, offset, _unused, lateral):
                return probe_collision_candidate(
                    image, index, offset, lateral,
                    path_rows=path_rows, path_count=24,
                    range_start=0, range_end=0, lower_limit=0, upper_limit=0,
                    clamp_indices=True, surface_vcall_result=0,
                    sample_surface=lambda point, row: sample_collision_surface(
                        world, point, row),
                    world_objects=(), traffic_rows=(), owner_address=OWNER)

            def unexpected_response(*_args):
                raise AssertionError('empty collision masks unexpectedly reached 0x51e460')

            search_surface_correction(
                owner, track_index, path_rows=path_rows, path_count=24,
                attempts=24, wrapped_ordering=False, wrapped_index=False,
                probe=probe, apply_response=unexpected_response,
                fallback_table=fallback_table,
                special_probe=False,
                alternate_track_side=bool(struct.unpack_from('<I', owner, 0x464)[0]),
                response_mode=bool(struct.unpack_from('<I', owner, 0xDF4)[0] & 0x800),
                index_is_rejected=lambda index: track_index_is_rejected(
                    index, range_start=0, range_end=0,
                    lower_limit=0, upper_limit=0))

        callbacks = EnvironmentCallbacks(
            world, adjust_contact, lambda _: None,
            struct.unpack('<f', struct.pack('<f', step))[0])
        translated = bytearray(record)
        environment_step(translated, callbacks=callbacks,
                         environment_enabled=True)
        if original != translated:
            differences = [index for index, (left, right)
                           in enumerate(zip(original, translated)) if left != right]
            raise AssertionError(
                f'failed-lookup correction mismatch case={case} '
                f'status={status} step={step} bytes='
                f'{[hex(index) for index in differences[:24]]}; '
                f'native={[(hex(i), original[i:i+4].hex()) for i in differences[:12]]}; '
                f'python={[(hex(i), translated[i:i+4].hex()) for i in differences[:12]]}')
    return cases


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', type=Path)
    parser.add_argument('--cases', type=int, default=128)
    args = parser.parse_args()
    print(f'0x51e940 failed-lookup + translated 0x43ba40 search match '
          f'{verify(args.executable, args.cases)} complete owner images; '
          '0x43bd30 executes its empty-mask gate and 0x43b750 remains intercepted')


if __name__ == '__main__':
    main()
