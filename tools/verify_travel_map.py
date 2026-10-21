"""Compare travel-map marking and first allocation in 0x406a50."""
import argparse
import random
import struct
from pathlib import Path

from client.travel_map import (TRAVEL_MAP_RESOURCE, TravelMapCache,
                               mark_travel_map)
from tools.native_oracle import DynoOracle


TABLE = 0x71008000
GLOBAL_TABLE = 0x008E3ABC
GLOBAL_SIZE = 0x008E3AC0
ALLOCATOR = 0x006EE510


def verify(executable, cases=512):
    from unicorn import UC_HOOK_CODE

    oracle = DynoOracle(executable)
    cpu, reg = oracle.cpu, oracle.reg
    rng = random.Random(0x406A50)
    for case in range(cases):
        count = rng.randrange(1, 800)
        threshold = rng.randrange(1, 80)
        row = rng.randrange(count)
        step = rng.randint(-96, threshold + 20)
        size = count // 20 + 1
        initial = bytearray(rng.randbytes(size))
        cache = TravelMapCache(bytearray(initial))
        cpu.mem_write(TABLE, bytes(initial))
        cpu.mem_write(GLOBAL_TABLE, struct.pack('<I', TABLE))
        cpu.mem_write(0x00988E38, struct.pack('<I', count))
        cpu.mem_write(0x009AAA50, struct.pack('<I', threshold))
        oracle.call(0x00406A50, (row, step))
        original = bytes(cpu.mem_read(TABLE, size))
        mark_travel_map(cache, row, step, path_count=count,
                        step_threshold=threshold,
                        allocate=lambda *_: None)
        if original != bytes(cache.data):
            raise AssertionError(f'0x406a50 existing-table mismatch case {case}: '
                f'row={row}, step={step}, count={count}, threshold={threshold}, '
                f'native={original.hex()}, python={cache.data.hex()}')

    allocation_cases = 32
    for case in range(allocation_cases):
        count = rng.randrange(1, 800)
        threshold = rng.randrange(1, 50)
        row = rng.randrange(count)
        step = rng.randrange(threshold)
        size = count // 20 + 1
        allocated = bytearray([0xa5] * size)
        allocator_calls = []
        cpu.mem_write(TABLE, bytes(allocated))
        cpu.mem_write(GLOBAL_TABLE, struct.pack('<I', 0))
        cpu.mem_write(GLOBAL_SIZE, struct.pack('<I', 0))
        cpu.mem_write(0x00988E38, struct.pack('<I', count))
        cpu.mem_write(0x009AAA50, struct.pack('<I', threshold))

        def intercept(machine, address, _code_size, _data):
            if address != ALLOCATOR:
                return
            stack = machine.reg_read(reg.UC_X86_REG_ESP)
            resource, requested, flags = struct.unpack(
                '<3I', machine.mem_read(stack + 4, 12))
            allocator_calls.append((resource, requested, flags))
            machine.reg_write(reg.UC_X86_REG_EAX, TABLE)
            return_address = struct.unpack('<I', machine.mem_read(stack, 4))[0]
            # 0x406a50's cdecl caller removes the three arguments itself.
            machine.reg_write(reg.UC_X86_REG_ESP, stack + 4)
            machine.reg_write(reg.UC_X86_REG_EIP, return_address)

        hook = cpu.hook_add(UC_HOOK_CODE, intercept)
        try:
            oracle.call(0x00406A50, (row, step), instruction_limit=100000)
        finally:
            cpu.hook_del(hook)
        original = bytes(cpu.mem_read(TABLE, size))
        native_size = struct.unpack('<I', cpu.mem_read(GLOBAL_SIZE, 4))[0]
        cache = TravelMapCache()
        python_calls = []

        def allocate(resource, requested, flags):
            python_calls.append((resource, requested, flags))
            return bytearray(allocated)

        mark_travel_map(cache, row, step, path_count=count,
                        step_threshold=threshold, allocate=allocate)
        if original != bytes(cache.data) or native_size != cache.capacity:
            raise AssertionError(f'0x406a50 allocation mismatch case {case}: '
                f'native_size={native_size}, python_size={cache.capacity}, '
                f'native={original.hex()}, python={cache.data.hex()}')
        expected = [(TRAVEL_MAP_RESOURCE, size, 0)]
        if allocator_calls != expected or python_calls != expected:
            raise AssertionError(f'0x406a50 allocator args mismatch case {case}: '
                f'native={allocator_calls}, python={python_calls}, expected={expected}')
    return cases + allocation_cases


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', type=Path)
    parser.add_argument('--cases', type=int, default=512)
    args = parser.parse_args()
    count = verify(args.executable, args.cases)
    print(f'0x406a50 travel-map updates match {count} original cases, '
          'including first allocation with the resource allocator intercepted')


if __name__ == '__main__':
    main()
