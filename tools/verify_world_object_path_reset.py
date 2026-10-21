"""Compare the path/reset state machine at 0x43f090 with the original."""
import argparse
import random
import struct
from pathlib import Path

from client.world_object_path_reset import PathResetGlobals, update_path_reset_state
from client.travel_map import TravelMapCache, mark_travel_map
from tools.native_oracle import DynoOracle

OWNER = 0x72002000
INTERFACE = 0x71006000
VTABLE = 0x71006100
VIRTUAL = 0x71006200
TRAVEL_MAP = 0x71007000


def _write_global(cpu, address, value):
    cpu.mem_write(address, struct.pack('<I', value & 0xffffffff))


def verify(executable, cases=128):
    from unicorn import UC_HOOK_CODE

    oracle = DynoOracle(executable)
    cpu, reg = oracle.cpu, oracle.reg
    rng = random.Random(0x43F090)
    for case in range(cases):
        path_count = rng.randrange(24, 120)
        wrap_reference = rng.randrange(path_count)
        secondary_reference = (wrap_reference if case % 3 == 0
                               else rng.randrange(path_count))
        environment_mode = case % 2
        designated_mode = rng.randrange(0, 5)
        globals_ = PathResetGlobals(
            path_count=path_count,
            wrap_reference=wrap_reference,
            secondary_reference=secondary_reference,
            multi_segment=case % 2,
            step_threshold=rng.randrange(1, 30),
            designated_mode=designated_mode,
            environment_mode=environment_mode)
        initial = bytearray(rng.randbytes(0x1c98))
        old_index = rng.randrange(path_count)
        new_index = rng.randrange(path_count)
        if case % 11 == 0:
            new_index = old_index
        flags = rng.getrandbits(32) & ~(0x800 | 0x400 | 0x1000)
        if case & 1:
            flags |= 0x800
        if case & 2:
            flags |= 0x400
        struct.pack_into('<i', initial, 0x364, old_index)
        struct.pack_into('<i', initial, 0x370, new_index)
        struct.pack_into('<i', initial, 0x464,
                         designated_mode if case % 4 == 0 else designated_mode + 1)
        struct.pack_into('<i', initial, 0x47c, rng.randrange(0, 40))
        struct.pack_into('<i', initial, 0x480, rng.randrange(-2, 4))
        struct.pack_into('<I', initial, 0xdf4, flags)
        query_result = 1 if case % 7 == 0 else 0
        virtual_calls = []
        notifications = []
        advances = []

        cpu.mem_write(OWNER, bytes(initial))
        _write_global(cpu, 0x00A65BD0, INTERFACE)
        _write_global(cpu, INTERFACE, VTABLE)
        _write_global(cpu, VTABLE + 0x10, VIRTUAL)
        for address, value in (
                (0x00988E38, path_count),
                (0x009AAA50, globals_.step_threshold),
                (0x009AAA78, wrap_reference),
                (0x009AAA7C, secondary_reference),
                (0x009AAA9C, globals_.multi_segment),
                (0x009AA9A0, designated_mode),
                (0x00AA459C, environment_mode),
                (0x008E3ABC, TRAVEL_MAP)):
            _write_global(cpu, address, value)
        cpu.mem_write(TRAVEL_MAP, bytes(path_count // 20 + 1))

        def intercept(machine, address, _size, _data):
            if address == VIRTUAL:
                virtual_calls.append(True)
                stack = machine.reg_read(reg.UC_X86_REG_ESP)
                return_address = struct.unpack('<I', machine.mem_read(stack, 4))[0]
                machine.reg_write(reg.UC_X86_REG_EAX, query_result)
                machine.reg_write(reg.UC_X86_REG_ESP, stack + 12)
                machine.reg_write(reg.UC_X86_REG_EIP, return_address)
            elif address == 0x00406A50:
                stack = machine.reg_read(reg.UC_X86_REG_ESP)
                args = struct.unpack('<2I', machine.mem_read(stack + 4, 8))
                notifications.append(args)
            elif address == 0x00468CC0:
                advances.append(True)

        hook = cpu.hook_add(UC_HOOK_CODE, intercept)
        try:
            oracle.call(0x0043F090, (OWNER,), instruction_limit=200000)
        finally:
            cpu.hook_del(hook)
        original = bytes(cpu.mem_read(OWNER, 0x1c98))

        translated = bytearray(initial)
        python_notifications = []
        python_advances = []
        travel_cache = TravelMapCache(bytearray(path_count // 20 + 1))
        update_path_reset_state(
            translated, globals_=globals_,
            interface_query=lambda selector, _owner: query_result,
            notify_track_change=lambda index, counter: (
                python_notifications.append((index, counter)),
                mark_travel_map(travel_cache, index, counter,
                    path_count=path_count,
                    step_threshold=globals_.step_threshold,
                    allocate=lambda *_: None)),
            advance_state=lambda _owner: python_advances.append(True))
        expected_notifications = ([(new_index, struct.unpack_from('<i', initial, 0x47c)[0])]
                                  if struct.unpack_from('<i', initial, 0x464)[0] == designated_mode
                                  and environment_mode == 0 and query_result == 0
                                  and new_index != old_index else [])
        if original != translated:
            differences = [i for i, (left, right) in enumerate(zip(original, translated))
                           if left != right]
            raise AssertionError(f'0x43f090 owner mismatch case {case}; '
                                 f'bytes {[hex(i) for i in differences[:20]]}; '
                                 f'original={[(hex(i), original[i:i+4].hex()) for i in differences[:8]]}; '
                                 f'python={[(hex(i), translated[i:i+4].hex()) for i in differences[:8]]}')
        if notifications != expected_notifications or python_notifications != expected_notifications:
            raise AssertionError(f'0x43f090 notification mismatch case {case}: '
                                 f'native={notifications} python={python_notifications} '
                                 f'expected={expected_notifications}')
        if len(advances) != len(python_advances):
            raise AssertionError(f'0x43f090 child-call mismatch case {case}: '
                                 f'native={len(advances)} python={len(python_advances)}')
        native_map = bytes(cpu.mem_read(TRAVEL_MAP, path_count // 20 + 1))
        if native_map != bytes(travel_cache.data):
            raise AssertionError(f'0x406a50 travel-map mismatch case {case}: '
                                 f'native={native_map.hex()} python={travel_cache.data.hex()}')
        if bool(virtual_calls) is False:
            raise AssertionError(f'case {case} did not execute the interface gate')
    return cases


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', type=Path)
    parser.add_argument('--cases', type=int, default=128)
    args = parser.parse_args()
    count = verify(args.executable, args.cases)
    print(f'0x43f090 path/reset state, travel-map writes, and child calls match '
          f'{count} original cases; only the virtual gate uses selected returns')


if __name__ == '__main__':
    main()
