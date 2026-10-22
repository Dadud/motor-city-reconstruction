"""Compare the 0x426af0/0x426b40 sphere gates against mcity.exe."""
import argparse
import json
import random
import struct

from client.collision_spatial_hash import (mark_sphere_neighbors,
                                           mark_spatial_hash_neighbors,
                                           sphere_overlap)
from tools.native_oracle import DynoOracle


OWNER = 0x71008000
MEMBERS = 0x71002000
HEADS = 0x0097BCD0
CELL = 3
OBJECT_ARRAY = 0x0092C478
OBJECT_COUNT = 0x0097C180
CELL_TABLE_POINTER = 0x0097C408
CELL_TABLE = 0x71008000


def _body(position, radius, active=0):
    image = bytearray(0x4f8)
    image[4] = active
    struct.pack_into('<3f', image, 8, *position)
    struct.pack_into('<f', image, 0xd8, radius)
    return image


def _native_mark(oracle, owner, members, linked):
    cpu = oracle.cpu
    cpu.mem_write(OWNER, bytes(owner))
    next_by_address = {address: (linked[position + 1]
                                 if position + 1 < len(linked) else 0)
                       for position, address in enumerate(linked)}
    for index, image in enumerate(members):
        address = MEMBERS + index * 0x600
        struct.pack_into('<I', image, 0x4f4, next_by_address[address])
        cpu.mem_write(address, bytes(image))
    cpu.mem_write(HEADS + 4 * CELL,
                  struct.pack('<I', linked[0] if linked else 0))
    oracle.call(0x426b40, (OWNER, CELL), instruction_limit=200_000)
    return [bytes(cpu.mem_read(MEMBERS + index * 0x600, 0x4f8))
            for index in range(len(members))]


def compare(executable, cases=256):
    if type(cases) is not int or cases < 1:
        raise ValueError('case count must be positive')
    oracle = DynoOracle(executable)
    rng = random.Random(0x426B40)
    compared = 0
    marked = 0
    direct_gate_cases = 0
    for case in range(cases):
        count = case % 12
        owner_position = tuple(rng.uniform(-30., 30.) for _ in range(3))
        owner = _body(owner_position, rng.uniform(.05, 5.))
        owner_radius = struct.unpack_from('<f', owner, 0xd8)[0]
        members, pointers = [], []
        for index in range(count):
            if index % 2 == 1 and index % 7 != 0:
                radius = owner_radius * .4
                position = (owner_position[0] + owner_radius * .5,
                            owner_position[1], owner_position[2])
            else:
                position = tuple(rng.uniform(-35., 35.) for _ in range(3))
                radius = rng.uniform(.05, 5.)
            members.append(_body(position, radius,
                                 active=1 if index % 7 == 0 else 0))
            pointers.append(MEMBERS + index * 0x600)
        linked = list(reversed(pointers))
        expected = [bytearray(image) for image in members]
        next_by_address = {address: (linked[position + 1]
                                     if position + 1 < len(linked) else 0)
                           for position, address in enumerate(linked)}
        for index, image in enumerate(expected):
            struct.pack_into('<I', image, 0x4f4,
                             next_by_address[MEMBERS + index * 0x600])
        expected_marked = mark_sphere_neighbors(owner, expected)
        actual = _native_mark(oracle, owner, [bytearray(image) for image in members], linked)
        if actual != [bytes(image) for image in expected]:
            for index, (got, want) in enumerate(zip(actual, expected)):
                if got != bytes(want):
                    offset = next(i for i, (a, b) in enumerate(zip(got, want)) if a != b)
                    raise AssertionError(
                        f'case {case}, member {index}, byte {offset:#x}: '
                        f'native {got[offset]:#x} != translated {want[offset]:#x}; '
                        f'expected mark count {expected_marked}')
        marked += expected_marked
        compared += count

        if case < min(128, cases):
            other = members[0] if members else _body(owner_position, 1.)
            # 0x426af0 takes candidate/owner XYZ pointers and a float radius sum.
            oracle.cpu.mem_write(OWNER + 0x1000, bytes(owner))
            oracle.cpu.mem_write(MEMBERS, bytes(other))
            radius = struct.unpack_from('<f', owner, 0xd8)[0] + struct.unpack_from('<f', other, 0xd8)[0]
            oracle.call(0x426af0,
                        (MEMBERS + 8, OWNER + 0x1008,
                         struct.unpack('<I', struct.pack('<f', radius))[0]),
                        instruction_limit=1000)
            actual_gate = oracle.cpu.reg_read(oracle.reg.UC_X86_REG_EAX) & 0xff
            expected_gate = int(sphere_overlap(owner, other))
            if actual_gate != expected_gate:
                raise AssertionError(
                    f'case {case}: 0x426af0 returned {actual_gate} != {expected_gate}')
            direct_gate_cases += 1
    hash_cases = min(128, cases)
    hash_members = 0
    for case in range(hash_cases):
        count = 1 + case % 12
        expected = []
        cells = {}
        cell_slots = {}
        for index in range(count):
            position = tuple(rng.uniform(-5., 5.) for _ in range(3))
            image = _body(position, rng.uniform(.2, 2.),
                          active=1 if rng.randrange(3) else 0)
            cell = rng.randrange(8)
            struct.pack_into('<I', image, 0x374, cell)
            expected.append(image)
            cells.setdefault(cell, []).append(image)
        for cell in range(8):
            cell_slots[cell] = tuple(rng.choice((-1, *range(8)))
                                     for _ in range(8))
        body_addresses = [OBJECT_ARRAY + index * 0x4f8 for index in range(count)]
        next_by_address = {}
        for group in cells.values():
            addresses = [body_addresses[expected.index(image)] for image in group]
            for index, address in enumerate(addresses):
                next_by_address[address] = addresses[index + 1] if index + 1 < len(addresses) else 0
        for index, image in enumerate(expected):
            struct.pack_into('<I', image, 0x4f4, next_by_address.get(body_addresses[index], 0))
        translated = [bytearray(image) for image in expected]
        translated_cells = {}
        for image in translated:
            translated_cells.setdefault(struct.unpack_from('<I', image, 0x374)[0], []).append(image)
        mark_spatial_hash_neighbors(translated, translated_cells, cell_slots)

        cpu = oracle.cpu
        oracle._reset()
        cpu.mem_write(OBJECT_COUNT, struct.pack('<I', count))
        cpu.mem_write(CELL_TABLE_POINTER, struct.pack('<I', CELL_TABLE))
        cpu.mem_write(HEADS, bytes(300 * 4))
        cpu.mem_write(CELL_TABLE, bytes(8 * 0x6c4))
        for cell, slots in cell_slots.items():
            cpu.mem_write(CELL_TABLE + cell * 0x6c4 + 0x6a4,
                          struct.pack('<8i', *slots))
        for index, image in enumerate(expected):
            cpu.mem_write(body_addresses[index], bytes(image))
        for cell, group in cells.items():
            addresses = [body_addresses[expected.index(image)] for image in group]
            cpu.mem_write(HEADS + cell * 4, struct.pack('<I', addresses[0]))
        cpu.ctl_remove_cache(0x426bc0, 0x426d05)
        oracle.call(0x426bc0, instruction_limit=2_000_000)
        native = [bytes(cpu.mem_read(address, 0x4f8)) for address in body_addresses]
        wanted = [bytes(image) for image in translated]
        if native != wanted:
            for index, (got, want) in enumerate(zip(native, wanted)):
                if got != want:
                    offset = next(i for i, (a, b) in enumerate(zip(got, want)) if a != b)
                    raise AssertionError(
                        f'0x426bc0 case {case}, body {index}, byte {offset:#x}: '
                        f'native {got[offset]:#x} != translated {want[offset]:#x}')
        hash_members += count
    return {'entry': '0x426b40',
            'linked_list_cases': cases, 'candidate_bodies': compared,
            'marked_inactive_candidates': marked,
            'direct_gate_cases': direct_gate_cases,
            'nine_cell_cases': hash_cases, 'nine_cell_bodies': hash_members,
            'entries': ['0x426af0', '0x426b40', '0x426bc0'],
            'scope': 'original 0x426b40, 0x426af0 and 0x426bc0 entries with supplied body records'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    parser.add_argument('--cases', type=int, default=256)
    args = parser.parse_args()
    print(json.dumps(compare(args.executable, args.cases)))
