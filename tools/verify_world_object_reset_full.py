"""Compare composed 0x43b750 source with the original through final dispatch."""
import argparse
import random
import struct
from pathlib import Path

from client.world_object_path_reset import PathResetGlobals
from client.travel_map import TravelMapCache
from client.world_object_reset import (OWNER_SIZE, WheelResetCache,
    WorldObjectResetServices, reset_world_object, reset_world_object_drive_state,
    reset_world_object_geometry, reset_world_object_track_rate_pipeline,
    reset_wheel_records, drive_reset_state_result)
from tools.native_oracle import DynoOracle


OWNER = 0x72002000
PROFILE = 0x71005000
TRACK_TABLE = 0x71000000
INTERFACE = 0x71006000
VTABLE = 0x71006100
QUERY = 0x71006200
FINAL = 0x71006300
TRAVEL_MAP = 0x71008000


def _return(machine, reg, argument_count, result=None):
    stack = machine.reg_read(reg.UC_X86_REG_ESP)
    return_address = struct.unpack('<I', machine.mem_read(stack, 4))[0]
    if result is not None:
        machine.reg_write(reg.UC_X86_REG_EAX, result & 0xffffffff)
    machine.reg_write(reg.UC_X86_REG_ESP, stack + 4 + argument_count * 4)
    machine.reg_write(reg.UC_X86_REG_EIP, return_address)


def verify(executable, cases=64):
    from unicorn import UC_HOOK_CODE

    oracle = DynoOracle(executable)
    cpu, reg = oracle.cpu, oracle.reg
    rng = random.Random(0x43B750)
    for case in range(cases):
        path_count = rng.randrange(24, 96)
        primary_count = rng.choice((0, path_count, path_count + 3))
        origin = rng.randrange(path_count)
        secondary = origin if case % 3 == 0 else rng.randrange(path_count)
        threshold = rng.randrange(1, 20)
        multi = case & 1
        wrapped = (case >> 1) & 1
        reverse = (case >> 2) & 1
        designated = rng.randrange(1, 20)
        outer_gate = case & 1
        environment = case & 1
        mouse_enabled = case & 1
        mouse_initialized = (case >> 1) & 1
        input_mode = case % 6
        mouse_x = 100 + case
        mouse_y = 200 + case
        globals_ = PathResetGlobals(path_count, origin, secondary, multi,
                                    threshold, designated, environment)
        profile = bytearray(rng.randbytes(0x690))
        struct.pack_into('<f', profile, 0x20, rng.uniform(0.2, 5.0))
        struct.pack_into('<f', profile, 0x374, rng.uniform(0.2, 5.0))
        struct.pack_into('<I', profile, 0x68c, 1)
        struct.pack_into('<I', profile, 0x6c, rng.randrange(10, 300))
        struct.pack_into('<i', profile, 0x70, rng.randrange(0, 30))

        initial = bytearray(rng.randbytes(OWNER_SIZE))
        old_index = rng.randrange(path_count)
        new_index = rng.randrange(path_count)
        if case % 7 == 0:
            new_index = old_index
        struct.pack_into('<I', initial, 0x1c94, PROFILE)
        struct.pack_into('<i', initial, 0x364, old_index)
        struct.pack_into('<i', initial, 0x370, new_index)
        struct.pack_into('<i', initial, 0x464,
                         designated if case % 5 == 0 else designated + 1)
        struct.pack_into('<i', initial, 0x47c, rng.randrange(0, 8))
        struct.pack_into('<i', initial, 0x480, rng.randrange(0, 4))
        struct.pack_into('<i', initial, 0x5ac, rng.randrange(0, 5))
        for offset in (0x78, 0x7c, 0x80, 0x84, 0x88, 0x8c,
                       0x90, 0x94, 0x98):
            struct.pack_into('<f', initial, offset, rng.uniform(-5, 5))
        struct.pack_into('<i', initial, 0xac0, rng.choice((-12, -3, 1, 7, 24)))
        struct.pack_into('<f', initial, 0x1898, rng.uniform(-500, 500))
        struct.pack_into('<f', initial, 0x1894, rng.uniform(-500, 500))
        struct.pack_into('<f', initial, 0xad4, rng.uniform(0.0, 1.5))
        struct.pack_into('<f', initial, 0xadc, rng.uniform(-2, 30))
        struct.pack_into('<f', initial, 0xacc, rng.uniform(-2, 30))
        for offset in (0x1810, 0x1814, 0x1818, 0x181c):
            struct.pack_into('<f', initial, offset, rng.uniform(0.2, 4.0))
        struct.pack_into('<f', initial, 0x18ec, rng.uniform(1, 100))
        struct.pack_into('<f', initial, 0x18f0, rng.uniform(1, 100))

        table = bytearray(path_count * 0x1c)
        for row in range(path_count):
            table[row * 0x1c + 0x18] = rng.randrange(0, 80)
            table[row * 0x1c + 0x19] = rng.randrange(0, 80)
        cpu.mem_write(OWNER, bytes(initial))
        cpu.mem_write(PROFILE, bytes(profile))
        cpu.mem_write(TRACK_TABLE, bytes(table))
        travel_cache = TravelMapCache(bytearray(path_count // 20 + 1))
        cpu.mem_write(TRAVEL_MAP, bytes(travel_cache.data))
        for address, value in (
            # These globals feed the wheel reset record's divisor slot. Use
            # the valid 1.0f operational value seen on this reset path.
            (0x0098C468, 0x3f800000),
            (0x0098C46C, rng.getrandbits(32)),
            (0x0098C474, 0x3f800000),
            (0x009AAA98, primary_count), (0x00988E38, path_count),
            (0x009AAA50, threshold), (0x009AAA54, reverse),
            (0x009AAA74, wrapped), (0x009AAA78, origin),
            (0x009AAA7C, secondary), (0x009AAA9C, multi),
            (0x009AA9A0, designated), (0x00AA459C, environment),
            (0x009E1644, mouse_enabled), (0x009E1640, mouse_initialized),
            (0x009E1674, mouse_x), (0x009E1678, mouse_y),
            (0x00AA4598, input_mode),
            (0x00ACAe68, rng.randrange(2, 8)), (0x008E3AB8, TRACK_TABLE),
            (0x008E3ABC, TRAVEL_MAP),
            (0x0083B638, 0), (0x00A65BD0, INTERFACE)):
            cpu.mem_write(address, struct.pack('<I', value))
        selected_owner = OWNER if case % 3 == 0 else 0x12340000 + case
        cpu.mem_write(0x0098C1E8 + designated * 4,
                      struct.pack('<I', selected_owner))
        result_mask = 0x00000001 if case & 2 else 0
        cpu.mem_write(0x009ABB04, struct.pack('<I', result_mask))
        # The original compares the adjacent constants as x87 values; preserve
        # the exact executable data already loaded by DynoOracle.
        cpu.mem_write(INTERFACE, struct.pack('<I', VTABLE))
        cpu.mem_write(VTABLE + 0x10, struct.pack('<I', QUERY))
        cpu.mem_write(VTABLE + 0x14, struct.pack('<I', FINAL))

        cache = WheelResetCache(False, 0.0)
        shared_reset = struct.unpack_from('<I', cpu.mem_read(0x0098C468, 4))[0]
        metadata = struct.unpack_from('<I', cpu.mem_read(0x0098C46C, 4))[0]
        motion = struct.unpack_from('<I', cpu.mem_read(0x0098C474, 4))[0]

        def reset_component(owner):
            return reset_wheel_records(
                owner, cache=cache,
                profile_scale=struct.unpack_from('<f', profile, 0x20)[0])

        def reset_drive(owner):
            return drive_reset_state_result(
                owner, owner_address=OWNER, selected_owner=selected_owner,
                result_mask=result_mask)

        def reset_drive_child(owner):
            return reset_world_object_drive_state(
                owner, profile, reset_drive_state=reset_drive,
                interface_result=0)

        services = WorldObjectResetServices(
            shared_reset_value=shared_reset, profile=profile,
            path_globals=globals_, shared_reset_generation=shared_reset,
            shared_reset_metadata=metadata,
            primary_path_count=primary_count, fallback_path_count=path_count,
            path_origin=origin, secondary_path_origin=secondary,
            wrapped_path_mode=wrapped, reverse_path_mode=reverse,
            reset_motion_value=motion, track_rows=table,
            default_track_attribute=0,
            track_rate_count=struct.unpack_from('<I',
                cpu.mem_read(0x00ACAe68, 4))[0],
            designated_mode=designated,
            mouse_controller_enabled=mouse_enabled,
            mouse_controller_initialized=mouse_initialized,
            mouse_input_mode=input_mode,
            mouse_environment_mode=environment,
            mouse_position_x=mouse_x,
            mouse_position_y=mouse_y,
            set_mouse_state=lambda _selector, _value: True,
            virtual_reset_gate=lambda selector, _owner:
                outer_gate if selector == 0x0f else 0,
            reset_drive_state=reset_drive, reset_component=reset_component,
            path_interface_query=lambda selector, _owner: 0 if selector == 0x16 else 1,
            advance_path_state=lambda _owner: None,
            travel_map_cache=travel_cache,
            allocate_travel_map=lambda _resource, size, _flags: bytearray(size),
            designated_mode_action=lambda: None,
            complete_interface_reset=lambda *_: None)

        translated = bytearray(initial)
        reset_world_object(translated, services=services)
        native_calls = []

        def intercept(machine, address, _size, _data):
            if address == 0x0053D640:
                native_calls.append('geometry')
                owner = bytearray(machine.mem_read(OWNER, OWNER_SIZE))
                reset_world_object_geometry(owner,
                    reset_component=reset_component,
                    update_attachment=reset_drive_child)
                machine.mem_write(OWNER, bytes(owner))
                _return(machine, reg, 0)
            elif address == QUERY:
                stack = machine.reg_read(reg.UC_X86_REG_ESP)
                selector = struct.unpack('<I', machine.mem_read(stack + 4, 4))[0]
                native_calls.append(('query', selector))
                _return(machine, reg, 2,
                        0 if selector == 0x16 else outer_gate)
            elif address == 0x0053D7B0:
                native_calls.append('track-rate')
                stack = machine.reg_read(reg.UC_X86_REG_ESP)
                rate_bits = struct.unpack('<I', machine.mem_read(stack + 8, 4))[0]
                rate = struct.unpack('<f', struct.pack('<I', rate_bits))[0]
                owner = bytearray(machine.mem_read(OWNER, OWNER_SIZE))
                reset_world_object_track_rate_pipeline(
                    owner, rate, profile,
                    reset_component=reset_component,
                    reset_drive_state=reset_drive)
                machine.mem_write(OWNER, bytes(owner))
                _return(machine, reg, 0)
            elif address == 0x004AD4A0:
                native_calls.append('designated-action')
            elif address == 0x006EFAF0:
                stack = machine.reg_read(reg.UC_X86_REG_ESP)
                selector, value = struct.unpack('<II', machine.mem_read(stack + 4, 8))
                native_calls.append(('mouse-state', selector, value))
                _return(machine, reg, 2, 1)
            elif address == FINAL:
                native_calls.append('final-interface')
                _return(machine, reg, 2, 0)

        hook = cpu.hook_add(UC_HOOK_CODE, intercept)
        try:
            try:
                oracle.call(0x0043B750, (OWNER,), instruction_limit=500000)
            except Exception as error:
                raise AssertionError(f'case {case} original reset failed at '
                    f'EIP={cpu.reg_read(reg.UC_X86_REG_EIP):#x}, '
                    f'ESI={cpu.reg_read(reg.UC_X86_REG_ESI):#x}, '
                    f'ESP={cpu.reg_read(reg.UC_X86_REG_ESP):#x}; calls={native_calls}') from error
        finally:
            cpu.hook_del(hook)
        original = bytes(cpu.mem_read(OWNER, OWNER_SIZE))
        original_map = bytes(cpu.mem_read(TRAVEL_MAP, len(travel_cache.data)))
        if original_map != bytes(travel_cache.data):
            raise AssertionError(f'full reset travel-map mismatch case {case}: '
                f'native={original_map.hex()} python={travel_cache.data.hex()}')
        if original != bytes(translated):
            differences = [i for i, (left, right) in enumerate(zip(original, translated))
                           if left != right]
            raise AssertionError(f'full reset mismatch case {case}; '
                f'bytes {[hex(i) for i in differences[:32]]}; '
                f'native={[(hex(i), original[i:i+4].hex()) for i in differences[:12]]}; '
                f'python={[(hex(i), translated[i:i+4].hex()) for i in differences[:12]]}; '
                f'calls={native_calls}')
        required_calls = {'geometry', 'final-interface'}
        if outer_gate:
            required_calls.add('track-rate')
        if struct.unpack_from('<i', initial, 0x464)[0] == designated:
            required_calls.add('designated-action')
            if (mouse_enabled and mouse_initialized and environment == 0
                    and input_mode not in (4, 5)):
                if ('mouse-state', 3, mouse_x) not in native_calls or (
                        'mouse-state', 4, mouse_y) not in native_calls:
                    raise AssertionError(f'case {case} missing reset cursor setters: {native_calls}')
        if not required_calls <= set(native_calls):
            raise AssertionError(f'case {case} missed composed reset stages: {native_calls}')
    return cases


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', type=Path)
    parser.add_argument('--cases', type=int, default=64)
    args = parser.parse_args()
    print(f'0x43b750 composed reset matches {verify(args.executable, args.cases)} '
          'complete owner images through final virtual dispatch')


if __name__ == '__main__':
    main()
