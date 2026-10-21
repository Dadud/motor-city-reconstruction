"""Compare reconstructed game callback lists with original 0x567940."""
import argparse
import random
import struct
from pathlib import Path

from client.game_schedule import build_game_task_lists
from tools.native_oracle import DynoOracle


VEHICLE_COUNT = 0x0098C218
VEHICLE_ARRAY = 0x0098C1E8
WORLD_COUNT = 0x00AB84E0
WORLD_ARRAY = 0x00AB1848
CAPACITY_COUNT = 0x009AAAB8
PRIMARY_LIST = 0x00AA4594
SECONDARY_LIST = 0x00AA4590
VEHICLE_BASE = 0x72002000
WORLD_BASE = 0x72005000
PRIMARY_QUEUE = 0x72008000
SECONDARY_QUEUE = 0x7200C000


def _u32(cpu, address):
    return struct.unpack('<I', cpu.mem_read(address, 4))[0]


def _queue(cpu, address):
    capacity, count = struct.unpack('<2I', cpu.mem_read(address, 8))
    if count > 1000:
        raise AssertionError(f'native queue count {count} exceeds safety bound')
    entries = []
    for index in range(count):
        priority, callback, payload = struct.unpack(
            '<3I', cpu.mem_read(address + 8 + index * 16, 12))
        entries.append((priority, callback, payload))
    return capacity, tuple(entries)


def verify(executable, cases=64):
    from unicorn import UC_HOOK_CODE

    oracle = DynoOracle(executable)
    cpu, reg = oracle.cpu, oracle.reg
    rng = random.Random(0x567940)
    for case in range(cases):
        vehicle_count = rng.randrange(0, 7)
        world_count = rng.randrange(0, 7)
        capacity_count = rng.randrange(0, 5)
        vehicles = tuple(VEHICLE_BASE + index * 0x500
                         for index in range(vehicle_count))
        objects = tuple(WORLD_BASE + index * 0x500
                        for index in range(world_count))
        flags = tuple(rng.getrandbits(32) for _ in vehicles)
        payload = rng.getrandbits(32)

        cpu.mem_write(VEHICLE_COUNT, struct.pack('<I', vehicle_count))
        cpu.mem_write(WORLD_COUNT, struct.pack('<I', world_count))
        cpu.mem_write(CAPACITY_COUNT, struct.pack('<I', capacity_count))
        cpu.mem_write(VEHICLE_ARRAY,
                      b''.join(struct.pack('<I', value) for value in vehicles)
                      or bytes(4))
        cpu.mem_write(WORLD_ARRAY,
                      b''.join(struct.pack('<I', value) for value in objects)
                      or bytes(4))
        for address, value in zip(vehicles, flags):
            cpu.mem_write(address + 0x474, struct.pack('<I', value))

        allocations = []

        def intercept(machine, address, _size, _data):
            if address not in (0x00565CB0, 0x004870C0):
                return
            stack = machine.reg_read(reg.UC_X86_REG_ESP)
            ret = _u32(machine, stack)
            if address == 0x00565CB0:
                allocator, capacity = struct.unpack(
                    '<2I', machine.mem_read(stack + 4, 8))
                queue = PRIMARY_QUEUE if not allocations else SECONDARY_QUEUE
                allocations.append((queue, capacity, allocator))
                machine.mem_write(queue, struct.pack('<2I', capacity, 0))
                for index in range(capacity):
                    machine.mem_write(queue + 8 + index * 16,
                                      struct.pack('<4I', 0x7FFE, 0, 0, 0))
                machine.reg_write(reg.UC_X86_REG_EAX, queue)
                machine.reg_write(reg.UC_X86_REG_ESP, stack + 4)
                machine.reg_write(reg.UC_X86_REG_EIP, ret)
            elif address == 0x004870C0:
                machine.reg_write(reg.UC_X86_REG_EAX, payload)
                # The caller deliberately keeps the pushed priority argument
                # on the stack for its immediately following 0x565d20 call.
                machine.reg_write(reg.UC_X86_REG_ESP, stack + 4)
                machine.reg_write(reg.UC_X86_REG_EIP, ret)

        hook = cpu.hook_add(UC_HOOK_CODE, intercept)
        try:
            oracle.call(0x00567940, (), instruction_limit=1_000_000)
        finally:
            cpu.hook_del(hook)

        expected = build_game_task_lists(
            vehicles, objects, flags, payload, capacity_count)
        primary_pointer = _u32(cpu, PRIMARY_LIST)
        secondary_pointer = _u32(cpu, SECONDARY_LIST)
        if primary_pointer != PRIMARY_QUEUE or secondary_pointer != SECONDARY_QUEUE:
            raise AssertionError(f'case {case}: native list pointers were not captured')
        native_primary = _queue(cpu, primary_pointer)
        native_secondary = _queue(cpu, secondary_pointer)
        expected_primary = tuple((entry.priority, entry.callback, entry.payload)
                                 for entry in expected.primary)
        expected_secondary = tuple((entry.priority, entry.callback, entry.payload)
                                   for entry in expected.secondary)
        if (native_primary != (expected.primary_capacity, expected_primary) or
                native_secondary != (expected.secondary_capacity,
                                     expected_secondary)):
            raise AssertionError(
                f'0x567940 mismatch case={case} vehicles={vehicle_count} '
                f'world={world_count} capacity_source={capacity_count} '
                f'flags={flags} allocations={allocations}: native={native_primary,native_secondary}; '
                f'python={(expected.primary_capacity, expected_primary), (expected.secondary_capacity, expected_secondary)}')
        if len(allocations) != 2:
            raise AssertionError(f'case {case}: expected 2 native list allocations, got {allocations}')
    return cases


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', type=Path)
    parser.add_argument('--cases', type=int, default=64)
    args = parser.parse_args()
    print(f'0x567940 task-list capacities and ordered entries match '
          f'{verify(args.executable, args.cases)} original executions')


if __name__ == '__main__':
    main()
