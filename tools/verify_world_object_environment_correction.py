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
from client.world_object_path_reset import PathResetGlobals
from client.world_object_environment import EnvironmentCallbacks, environment_step
from client.travel_map import TravelMapCache
from client.world_object_reset import (OWNER_SIZE as RESET_OWNER_SIZE,
    WheelResetCache, WorldObjectResetServices, drive_reset_state_result,
    reset_world_object, reset_world_object_drive_state,
    reset_world_object_geometry, reset_wheel_records)
from tools.track_surface_cases import BASE, BLOCKS, PATH, fixture
from tools.native_oracle import DynoOracle


OWNER = 0x7100C000
OWNER_SIZE = 0x1C98
PROFILE = 0x7100A000
TRAVEL_MAP = 0x7100B000
INTERFACE = 0x71008000
VTABLE = 0x71008100
QUERY = 0x71008200
FINAL = 0x71008300


def _return(machine, reg, argument_count, result=None):
    stack = machine.reg_read(reg.UC_X86_REG_ESP)
    return_address = struct.unpack('<I', machine.mem_read(stack, 4))[0]
    if result is not None:
        machine.reg_write(reg.UC_X86_REG_EAX, result & 0xffffffff)
    machine.reg_write(reg.UC_X86_REG_ESP,
                      stack + 4 + argument_count * 4)
    machine.reg_write(reg.UC_X86_REG_EIP, return_address)


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
                               (0x009AAA50, 2), (0x009AAA54, 0),
                               (0x009AAA98, 0), (0x009AAA9C, 0),
                               (0x009AA9A0, 7),
                               (0x0098C218, 0), (0x0097C180, 0),
                               (0x008E3AB8, 0x71007000),
                               (0x008E3ABC, TRAVEL_MAP),
                               (0x00A65BD0, INTERFACE)):
            cpu.mem_write(address, struct.pack('<I', value))
        fallback_table = bytes(24 * 0x1c)
        cpu.mem_write(0x71007000, fallback_table)
        cpu.mem_write(INTERFACE, struct.pack('<I', VTABLE))
        cpu.mem_write(VTABLE + 0x10, struct.pack('<I', QUERY))
        cpu.mem_write(VTABLE + 0x14, struct.pack('<I', FINAL))
        cpu.mem_write(QUERY, b'\xb8\0\0\0\0\xc2\x08\0')
        cpu.mem_write(FINAL, b'\xb8\0\0\0\0\xc2\x08\0')

        record = bytearray(rng.randbytes(OWNER_SIZE))
        record[4] = 1
        record[6] = 1  # 0x51e940 selects 0x43bfd0 after lookup failure.
        struct.pack_into('<I', record, 0x464, 0)
        struct.pack_into('<I', record, 0x1C94, PROFILE)
        old_reset_index, new_reset_index = (
            (23, 0) if case % 2 == 0 else (0, 23))
        struct.pack_into('<i', record, 0x364, old_reset_index)
        struct.pack_into('<ii', record, 0x47C, 0, 0)
        struct.pack_into('<I', record, 0x5AC, 0)
        struct.pack_into('<I', record, 0xDF4, 0)
        struct.pack_into('<I', record, 0x474, 0)
        struct.pack_into('<i', record, 0xAC0, rng.choice((-12, -3, 1, 7, 24)))
        struct.pack_into('<f', record, 0x1898, rng.uniform(-500.0, 500.0))
        struct.pack_into('<f', record, 0x1894, rng.uniform(-500.0, 500.0))
        struct.pack_into('<f', record, 0xAD4, rng.uniform(0.0, 1.5))
        struct.pack_into('<f', record, 0xADC, rng.uniform(-2.0, 30.0))
        struct.pack_into('<f', record, 0xACC, rng.uniform(-2.0, 30.0))
        for offset in (0x1810, 0x1814, 0x1818, 0x181C):
            struct.pack_into('<f', record, offset, rng.uniform(0.2, 4.0))
        struct.pack_into('<2f', record, 0x18EC,
                         rng.uniform(1.0, 100.0), rng.uniform(1.0, 100.0))
        struct.pack_into('<3f', record, 8, x, rng.uniform(-2.0, 8.0), z)
        struct.pack_into('<3f', record, 0x358, x, rng.uniform(-2.0, 8.0), z)
        struct.pack_into('<3f', record, 0x14,
                         *(rng.uniform(-1.0, 1.0) for _ in range(3)))
        struct.pack_into('<9f', record, 0x78, 1, 0, 0, 0, 1, 0, 0, 0, 1)
        struct.pack_into('<66f', record, 0xE0,
                         *(rng.uniform(-1.0, 1.0) for _ in range(66)))
        record[0x370:0x370 + 68] = query
        struct.pack_into('<I', record, 0x370, new_reset_index)
        struct.pack_into('<I', record, 0x378, 1)
        struct.pack_into('<3f', record, 0x370 + 44, 0.0, 1.0, 0.0)
        status = (0, 1, -1, 17)[case % 4]
        struct.pack_into('<i', record, 0x36C, status)
        cpu.mem_write(OWNER, bytes(record))

        profile = bytearray(rng.randbytes(0x690))
        struct.pack_into('<f', profile, 0x20, rng.uniform(0.2, 5.0))
        struct.pack_into('<f', profile, 0x374, rng.uniform(0.2, 5.0))
        struct.pack_into('<I', profile, 0x68C, 1)
        struct.pack_into('<I', profile, 0x6C, rng.randrange(10, 300))
        struct.pack_into('<i', profile, 0x70, rng.randrange(0, 30))
        cpu.mem_write(PROFILE, bytes(profile))

        shared_reset = 0x3F800000
        metadata = rng.getrandbits(32)
        motion = 0x3F800000
        cpu.mem_write(0x0098C468, struct.pack('<I', shared_reset))
        cpu.mem_write(0x0098C46C, struct.pack('<I', metadata))
        cpu.mem_write(0x0098C474, struct.pack('<I', motion))
        track_rate_count = 2
        cpu.mem_write(0x00ACAE68, struct.pack('<I', track_rate_count))
        cpu.mem_write(TRAVEL_MAP, bytes(2))

        step = rng.uniform(-20.0, 20.0)
        cpu.mem_write(0x0098C470, struct.pack('<f', step))
        mode_active = bool(case & 1)
        mode_number = case % 2
        cpu.mem_write(0x00AA459C, struct.pack('<B', int(mode_active)))
        cpu.mem_write(0x00A6CC40, struct.pack('<I', mode_number))

        reset_cache = WheelResetCache(False, 0.0)
        travel_cache = TravelMapCache(bytearray(2))
        selected_owner = 0x12340000 + case

        def reset_component(owner):
            return reset_wheel_records(
                owner, cache=reset_cache,
                profile_scale=struct.unpack_from('<f', profile, 0x20)[0])

        def reset_drive(owner):
            return drive_reset_state_result(
                owner, owner_address=OWNER, selected_owner=selected_owner,
                result_mask=0)

        def reset_drive_child(owner):
            return reset_world_object_drive_state(
                owner, profile, reset_drive_state=reset_drive,
                interface_result=0)

        reset_services = WorldObjectResetServices(
            shared_reset_value=shared_reset, profile=bytes(profile),
            path_globals=PathResetGlobals(24, 0, 0, 0, 2, 7, 0),
            shared_reset_generation=shared_reset,
            shared_reset_metadata=metadata,
            primary_path_count=0, fallback_path_count=24,
            path_origin=0, secondary_path_origin=0,
            wrapped_path_mode=1, reverse_path_mode=0,
            reset_motion_value=motion, track_rows=fallback_table,
            default_track_attribute=0,
            track_rate_count=track_rate_count, designated_mode=7,
            virtual_reset_gate=lambda _selector, _owner: 0,
            reset_drive_state=reset_drive, reset_component=reset_component,
            path_interface_query=lambda _selector, _owner: 0,
            advance_path_state=lambda _owner: None,
            travel_map_cache=travel_cache,
            allocate_travel_map=lambda _resource, size, _flags: bytearray(size),
            designated_mode_action=lambda: None,
            mouse_controller_enabled=0, mouse_controller_initialized=0,
            mouse_input_mode=0, mouse_environment_mode=int(mode_active),
            mouse_position_x=0, mouse_position_y=0,
            set_mouse_state=lambda _selector, _value: True,
            complete_interface_reset=lambda *_args: None)

        native_calls = []

        def intercept_correction_children(machine, address, _size, _data):
            if address in (0x0043BFD0, 0x0043BA40, 0x0043BD30,
                           0x0043B750, FINAL):
                native_calls.append(address)
            if address == 0x0053D640:
                native_calls.append('0x53d640 translated geometry/reset')
                image = bytearray(machine.mem_read(OWNER, RESET_OWNER_SIZE))
                reset_world_object_geometry(
                    image, reset_component=reset_component,
                    update_attachment=reset_drive_child)
                machine.mem_write(OWNER, bytes(image))
                stack = machine.reg_read(reg.UC_X86_REG_ESP)
                _return(machine, reg, 0)

        hook = cpu.hook_add(UC_HOOK_CODE, intercept_correction_children)
        try:
            oracle.call(0x0051E940, (OWNER,), instruction_limit=1_000_000)
        finally:
            cpu.hook_del(hook)
        original = bytes(cpu.mem_read(OWNER, OWNER_SIZE))
        if native_calls != [0x0043BFD0, 0x0043BA40,
                            0x0043BD30, 0x0043B750,
                            '0x53d640 translated geometry/reset', FINAL]:
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
            world, adjust_contact,
            lambda owner: reset_world_object(owner, services=reset_services),
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
        if struct.unpack_from('<i', original, 0x364)[0] != new_reset_index:
            raise AssertionError(
                f'case {case} did not exercise path-reset publication: '
                f'old={old_reset_index} new={new_reset_index} '
                f'published={struct.unpack_from("<i", original, 0x364)[0]}')
    return cases


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', type=Path)
    parser.add_argument('--cases', type=int, default=128)
    args = parser.parse_args()
    print(f'0x51e940 failed-lookup with translated 0x43ba40/0x43b750 '
          f'matches {verify(args.executable, args.cases)} complete owner images; '
          'native 0x43bd30 mask gate and 0x53d640 geometry child are bridged')


if __name__ == '__main__':
    main()
