"""Compare the path-index helpers 0x406840 and 0x4066f0 with the original."""
import argparse
import random
import struct
from pathlib import Path

from client.track_topology import (path_index_is_forward, step_path_index,
                                   track_index_is_rejected,
                                   bounded_path_index, collision_search_bit,
                                   collision_search_slot)
from tools.native_oracle import DynoOracle


def verify(executable, cases=512):
    oracle = DynoOracle(executable)
    cpu = oracle.cpu
    rng = random.Random(0x406840)
    completed = 0
    for case in range(cases):
        count = rng.randint(1, 4096)
        current = rng.randrange(count)
        candidate = rng.randrange(count)
        wrapped = bool(case & 1)
        cpu.mem_write(0x00988E38, struct.pack('<I', count))
        cpu.mem_write(0x009AAA74, struct.pack('<I', int(not wrapped)))
        oracle.call(0x00406840, (current, candidate))
        original = bool(oracle.cpu.reg_read(oracle.reg.UC_X86_REG_EAX) & 0xff)
        translated = path_index_is_forward(
            count, current, candidate, wrapped_ordering=wrapped)
        if translated != original:
            raise AssertionError(f'0x406840 case {case}: '
                                 f'{count,current,candidate,wrapped}: '
                                 f'{original} != {translated}')
        completed += 1

    for case in range(cases):
        count = rng.randint(1, 4096)
        index = rng.randrange(count)
        offset = rng.randint(-2 * count, 2 * count)
        cpu.mem_write(0x00988E38, struct.pack('<I', count))
        cpu.mem_write(0x009AAA78, struct.pack('<I', 1))
        cpu.mem_write(0x009AAA7C, struct.pack('<I', 1))
        oracle.call(0x004066F0, (index, offset))
        original = oracle.cpu.reg_read(oracle.reg.UC_X86_REG_EAX)
        translated = step_path_index(index, offset, count)
        if (translated & 0xffffffff) != original:
            raise AssertionError(f'0x4066f0 case {case}: '
                                 f'{count,index,offset}: {original} != {translated}')
        completed += 1
    for case in range(cases):
        range_start = rng.randint(-128, 128)
        range_end = rng.randint(-128, 128)
        lower_limit = rng.randint(-32, 128)
        upper_limit = rng.randint(-32, 128)
        index = rng.randint(-128, 128)
        for address, value in ((0x009AAA78, range_start),
                               (0x009AAA7C, range_end),
                               (0x009AAA90, lower_limit),
                               (0x009AAA94, upper_limit)):
            cpu.mem_write(address, struct.pack('<i', value))
        oracle.call(0x00406960, (index,))
        original = bool(oracle.cpu.reg_read(oracle.reg.UC_X86_REG_EAX) & 0xff)
        translated = track_index_is_rejected(
            index, range_start=range_start, range_end=range_end,
            lower_limit=lower_limit, upper_limit=upper_limit)
        if translated != original:
            raise AssertionError(f'0x406960 case {case}: '
                                 f'{index,range_start,range_end,lower_limit,upper_limit}: '
                                 f'{original} != {translated}')
        completed += 1

    for case in range(cases):
        count = rng.randint(1, 4096)
        index = rng.randrange(count)
        offset = rng.randint(-2 * count, 2 * count)
        range_start = rng.randint(-128, 128)
        range_end = rng.randint(-128, 128)
        lower_limit = rng.randint(-32, 128)
        upper_limit = rng.randint(-32, 128)
        for address, value in ((0x00988E38, count),
                               (0x009AAA78, range_start),
                               (0x009AAA7C, range_end),
                               (0x009AAA90, lower_limit),
                               (0x009AAA94, upper_limit)):
            cpu.mem_write(address, struct.pack('<i', value))
        if range_start == range_end:
            range_end += 1
            cpu.mem_write(0x009AAA7C, struct.pack('<i', range_end))
        oracle.call(0x004066F0, (index, offset))
        original = oracle.cpu.reg_read(oracle.reg.UC_X86_REG_EAX)
        translated = step_path_index(
            index, offset, count, wrap_mode=False,
            index_is_rejected=lambda value: track_index_is_rejected(
                value, range_start=range_start, range_end=range_end,
                lower_limit=lower_limit, upper_limit=upper_limit))
        if (translated & 0xffffffff) != original:
            raise AssertionError(f'0x4066f0 clamped case {case}: '
                                 f'{count,index,offset,range_start,range_end,lower_limit,upper_limit}: '
                                 f'{original} != {translated}')
        completed += 1

    for case in range(cases):
        count = rng.randint(1, 4096)
        index = rng.randrange(count)
        offset = rng.randint(-2 * count, 2 * count)
        clamp = bool(case & 1)
        cpu.mem_write(0x00988E38, struct.pack('<I', count))
        cpu.mem_write(0x009AAA74, struct.pack('<I', int(clamp)))
        oracle.call(0x00406770, (index, offset))
        original = oracle.cpu.reg_read(oracle.reg.UC_X86_REG_EAX)
        translated = bounded_path_index(index, offset, count, clamp=clamp)
        if (translated & 0xffffffff) != original:
            raise AssertionError(f'0x406770 case {case}: '
                                 f'{count,index,offset,clamp}: '
                                 f'{original} != {translated}')
        completed += 1

    table = 0x71000000
    cpu.mem_write(0x0097C38C, struct.pack('<I', table))
    for case in range(cases):
        mask = rng.getrandbits(32)
        index = rng.randint(-10, 24)
        cpu.mem_write(table + 0x4c, struct.pack('<I', mask))
        oracle.call(0x00403320, (0, index))
        original = oracle.cpu.reg_read(oracle.reg.UC_X86_REG_EAX)
        translated = collision_search_bit(mask, index)
        if translated != original:
            raise AssertionError(f'0x403320 case {case}: '
                                 f'{mask,index}: {original} != {translated}')
        completed += 1

    for case in range(cases):
        left_step = rng.uniform(0.25, 20.0)
        right_step = rng.uniform(0.25, 20.0)
        offset = rng.uniform(-100.0, 100.0)
        cpu.mem_write(table + 0x38, struct.pack('<f', left_step))
        cpu.mem_write(table + 0x3c, struct.pack('<f', right_step))
        offset_bits = struct.unpack('<I', struct.pack('<f', offset))[0]
        oracle.call(0x004033B0, (0, offset_bits))
        original = oracle.cpu.reg_read(oracle.reg.UC_X86_REG_EAX)
        translated = collision_search_slot(left_step, right_step, offset)
        if translated != original:
            raise AssertionError(f'0x4033b0 case {case}: '
                                 f'{left_step,right_step,offset}: '
                                 f'{original} != {translated}')
        completed += 1
    return completed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', type=Path)
    parser.add_argument('--cases', type=int, default=512)
    args = parser.parse_args()
    print(f'0x406840, 0x4066f0, 0x406960, 0x406770, 0x403320, and 0x4033b0 match '
          f'{verify(args.executable, args.cases)} original calls, including '
          'clamped stepping with the actual rejection helper')


if __name__ == '__main__':
    main()
