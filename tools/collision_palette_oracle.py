"""Compare the 0x428500 palette transform and 0x428640 list walk to mcity.exe."""
import argparse
import json
import random
import struct

from client.collision_palette import adjust_color_records, adjust_color_words
from tools.native_oracle import DynoOracle


PALETTE = 0x71004000
GROUP = 0x71001000
RECORDS = 0x71002000
COLORS = 0x71005000
PERCENTAGES = (0x008914FC, 0x00891500, 0x00891504)


def _percentages(case, rng):
    choices = (-(1 << 31), -100, -1, 0, 50, 99, 100, 101,
               125, 150, (1 << 31) - 1)
    if case < len(choices):
        return (choices[case], choices[-case - 1], choices[(case * 3) % len(choices)])
    return tuple(rng.randrange(-(1 << 31), 1 << 31) for _ in range(3))


def _set_percentages(cpu, values):
    for address, value in zip(PERCENTAGES, values):
        cpu.mem_write(address, struct.pack('<I', value & 0xffffffff))


def compare(executable, cases=256):
    if type(cases) is not int or cases < 1:
        raise ValueError('case count must be positive')
    oracle = DynoOracle(executable)
    cpu = oracle.cpu
    rng = random.Random(0x428500)
    words_checked = 0
    list_groups = min(128, cases)
    list_records = 0
    for case in range(cases):
        count = 0 if case == 0 else rng.randrange(1, 65)
        percentages = _percentages(case, rng)
        values = [rng.getrandbits(32) for _ in range(count)]
        image = bytearray(struct.pack('<' + 'I' * count, *values)) if count else bytearray()
        expected = bytearray(image)
        adjust_color_words(expected, count, percentages)
        oracle._reset()
        _set_percentages(cpu, percentages)
        cpu.mem_write(PALETTE, bytes(image) or bytes(4))
        oracle.call(0x428500, (count, PALETTE), instruction_limit=500_000)
        actual = bytes(cpu.mem_read(PALETTE, count * 4)) if count else b''
        if actual != bytes(expected):
            raise AssertionError(f'0x428500 case {case}: transformed color words differ')
        words_checked += count

        if case < list_groups:
            group_count = case % 6
            group_rows = []
            arrays = []
            for row_index in range(group_count):
                color_count = rng.randrange(0, 12)
                colors = bytearray(struct.pack(
                    '<' + 'I' * color_count,
                    *(rng.getrandbits(32) for _ in range(color_count))))
                arrays.append(colors)
                group_rows.append((color_count, colors))
            expected_arrays = [bytearray(colors) for colors in arrays]
            expected_rows = tuple((row[0], image)
                                  for row, image in zip(group_rows, expected_arrays))
            adjust_color_records(expected_rows, percentages)
            oracle._reset()
            _set_percentages(cpu, percentages)
            cpu.mem_write(GROUP, struct.pack('<II', group_count, RECORDS))
            cpu.mem_write(RECORDS, bytes(0x24 + group_count * 0x38))
            for row_index, ((color_count, _), colors) in enumerate(zip(group_rows, arrays)):
                color_ptr = COLORS + row_index * 0x100
                row = RECORDS + 0x24 + row_index * 0x38
                cpu.mem_write(row, struct.pack('<I', color_count))
                cpu.mem_write(row + 8, struct.pack('<I', color_ptr))
                cpu.mem_write(color_ptr, bytes(colors) or bytes(4))
            oracle.call(0x428640, (GROUP,), instruction_limit=500_000)
            for row_index, colors in enumerate(expected_arrays):
                color_ptr = COLORS + row_index * 0x100
                actual_colors = bytes(cpu.mem_read(color_ptr, len(colors))) if colors else b''
                if actual_colors != bytes(colors):
                    raise AssertionError(
                        f'0x428640 case {case}, palette {row_index}: colors differ')
                list_records += len(colors) // 4
    return {'entries': ['0x428500', '0x428640'], 'direct_cases': cases,
            'color_words': words_checked, 'list_group_cases': list_groups,
            'list_color_words': list_records, 'all_bytes_matched': True,
            'scope': 'original color transform and pointer-based group traversal'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    parser.add_argument('--cases', type=int, default=256)
    args = parser.parse_args()
    print(json.dumps(compare(args.executable, args.cases)))
