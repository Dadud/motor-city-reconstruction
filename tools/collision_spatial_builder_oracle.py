"""Compare the complete 0x426770 spatial-candidate rebuild to mcity.exe."""
import argparse
import json
import random
import struct

from client.collision_spatial_hash import rebuild_collision_spatial_flags
from tools.native_oracle import DynoOracle


OBJECTS = 0x0092C478
OBJECT_COUNT = 0x0097C180
ROSTER_POINTERS = 0x0098C1E8
ROSTER_COUNT = 0x009AAAB8
CELL_POINTER = 0x0097C408
CELL_TABLE = 0x71008000
CANDIDATE_COUNT = 0x0097C398
CANDIDATE_POINTER = 0x0097C410
CANDIDATES = 0x71006000
CELL_COUNT = 8
OBJECT_STRIDE = 0x4F8


def _f32(value):
    return struct.unpack('<f', struct.pack('<f', value))[0]


def _body(rng, index, case):
    image = bytearray(OBJECT_STRIDE)
    image[4] = 1 if (index + case) % 3 else 0
    cell = (index * 3 + case) % CELL_COUNT
    struct.pack_into('<I', image, 0x374, cell)
    cluster = ((index + case) % 4) * 3.0
    position = (cluster + rng.uniform(-1.5, 1.5),
                rng.uniform(-.5, .5), rng.uniform(-1.5, 1.5))
    struct.pack_into('<3f', image, 8, *position)
    struct.pack_into('<f', image, 0xd8, rng.uniform(.2, 2.5))
    struct.pack_into('<f', image, 0x6c, 1. if (index + 2 * case) % 13 == 0 else 0.)
    struct.pack_into('<f', image, 0x3b4, rng.uniform(0., .2))
    struct.pack_into('<f', image, 0x18, rng.uniform(0., .4))
    struct.pack_into('<3f', image, 0x38,
                     *(rng.uniform(-.06, .06) for _ in range(3)))
    struct.pack_into('<h', image, 0x3bc, 1 if (index + case) % 5 == 0 else 0)
    struct.pack_into('<f', image, 0x350, rng.uniform(0., 3.))
    struct.pack_into('<3f', image, 0x14,
                     *(rng.uniform(-4., 4.) for _ in range(3)))
    struct.pack_into('<3f', image, 0x38,
                     *(rng.uniform(-.06, .06) for _ in range(3)))
    return image


def compare(executable, cases=128):
    if type(cases) is not int or cases < 1:
        raise ValueError('case count must be positive')
    oracle = DynoOracle(executable)
    cpu = oracle.cpu
    rng = random.Random(0x426770)
    body_total = 0
    roster_total = 0
    dynamic_records_total = 0
    for case in range(cases):
        count = 1 + case % 10
        bodies = [_body(rng, index, case) for index in range(count)]
        body_addresses = [OBJECTS + index * OBJECT_STRIDE for index in range(count)]
        roster_indices = [index for index in range(count)
                          if (index + case) % 2 == 0]
        neighbor_cells = {}
        for cell in range(CELL_COUNT):
            neighbors = [rng.randrange(CELL_COUNT) if rng.randrange(4) else -1
                         for _ in range(8)]
            neighbor_cells[cell] = tuple(neighbors)
        dynamic_records = []
        for index in range(case % 4):
            record = bytearray(0x78)
            source_body = bodies[(case + index) % count]
            center = struct.unpack_from('<3f', source_body, 8)
            center = tuple(_f32(value + rng.uniform(-2., 2.)) for value in center)
            struct.pack_into('<3f', record, 0, *center)
            struct.pack_into('<I', record, 0x30, 0 if (case + index) % 7 == 0 else 1)
            struct.pack_into('<I', record, 0x38, (case + index) % CELL_COUNT)
            struct.pack_into('<f', record, 0x48, rng.uniform(.2, 2.5))
            struct.pack_into('<I', record, 0x74, 0 if (case + index) % 5 == 0 else 0x12340000 + index)
            dynamic_records.append(record)
        expected = [bytearray(body) for body in bodies]
        expected_roster = [expected[index] for index in roster_indices]
        rebuild_collision_spatial_flags(
            expected, expected_roster, neighbor_cells, dynamic_records,
            body_addresses=body_addresses)

        oracle._reset()
        cpu.mem_write(OBJECT_COUNT, struct.pack('<I', count))
        cpu.mem_write(ROSTER_COUNT, struct.pack('<I', len(roster_indices)))
        roster_image = b''.join(struct.pack('<I', body_addresses[index])
                                for index in roster_indices)
        cpu.mem_write(ROSTER_POINTERS, roster_image or bytes(4))
        cpu.mem_write(CELL_POINTER, struct.pack('<I', CELL_TABLE))
        cpu.mem_write(CANDIDATE_COUNT, struct.pack('<I', len(dynamic_records)))
        cpu.mem_write(CANDIDATE_POINTER, struct.pack('<I', CANDIDATES))
        cpu.mem_write(CELL_TABLE, bytes(CELL_COUNT * 0x6C4))
        cpu.mem_write(CANDIDATES, bytes(max(1, len(dynamic_records)) * 0x78))
        for cell, slots in neighbor_cells.items():
            cpu.mem_write(CELL_TABLE + cell * 0x6C4 + 0x6A4,
                          struct.pack('<8i', *slots))
        for index, body in enumerate(bodies):
            cpu.mem_write(body_addresses[index], bytes(body))
        for index, record in enumerate(dynamic_records):
            cpu.mem_write(CANDIDATES + index * 0x78, bytes(record))
        cpu.ctl_remove_cache(0x426770, 0x426AE3)
        oracle.call(0x426770, instruction_limit=5_000_000)
        actual = [bytes(cpu.mem_read(address, OBJECT_STRIDE))
                  for address in body_addresses]
        wanted = [bytes(body) for body in expected]
        if actual != wanted:
            for index, (got, want) in enumerate(zip(actual, wanted)):
                if got != want:
                    offset = next(i for i, (a, b) in enumerate(zip(got, want)) if a != b)
                    raise AssertionError(
                        f'case {case}, body {index}, byte {offset:#x}: '
                        f'native {got[offset]:#x} != translated {want[offset]:#x}')
        body_total += count
        roster_total += len(roster_indices)
        dynamic_records_total += len(dynamic_records)
    return {'entry': '0x426770', 'cases': cases,
            'body_records': body_total, 'roster_records': roster_total,
            'dynamic_candidate_records': dynamic_records_total,
            'all_body_bytes_matched': True,
            'scope': 'original builder with explicit body, roster, neighbor-cell and candidate tables'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    parser.add_argument('--cases', type=int, default=128)
    args = parser.parse_args()
    print(json.dumps(compare(args.executable, args.cases)))
