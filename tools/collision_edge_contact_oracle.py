"""Compare edge-mask/contact helpers 0x42d900 and 0x45c870 to mcity.exe."""
import argparse
import json
import math
import random
import struct

from unicorn import UC_HOOK_CODE
from client.collision_edge_contact import (CollisionEdgeRecord,
                                           edge_crossing_mask,
                                           resolve_edge_contact)
from tools.native_oracle import DynoOracle


POLYGON = 0x71001000
OTHER = 0x71001100
QUERY = 0x71002000
NORMAL = 0x71002010
POINT = 0x71002020
HEIGHT = 0x71002030
WEIGHTS = 0x71003000
OTHER_WEIGHTS = 0x71003010
VERTICES = 0x71004000
OTHER_VERTICES = 0x71004100


def _record(oracle, address, weight_address, vertex_address, identity, vertices,
            weights):
    cpu = oracle.cpu
    cpu.mem_write(weight_address, bytes(weights))
    cpu.mem_write(address + 0x0c, struct.pack('<I', identity))
    cpu.mem_write(address + 0x10, struct.pack('<4I', *(vertex_address + i * 0x10
                                                       for i in range(4))))
    for index, vertex in enumerate(vertices):
        cpu.mem_write(vertex_address + index * 0x10, struct.pack('<3f', *vertex))
    return CollisionEdgeRecord(identity, tuple(vertices), bytes(weights))


def compare(executable, count=256):
    if type(count) is not int or count < 1:
        raise ValueError('case count must be positive')
    rng = random.Random(0x45C870)
    oracle = DynoOracle(executable)
    cpu = oracle.cpu
    maximum_output_error = 0.0
    mask_cases = contact_cases = 0
    for index in range(count):
        center_x, center_z = rng.uniform(-10, 10), rng.uniform(-10, 10)
        width, depth = rng.uniform(.2, 3), rng.uniform(.2, 3)
        angle = rng.uniform(-math.pi, math.pi)
        cosine, sine = math.cos(angle), math.sin(angle)
        base = ((-width, -depth), (width, -depth),
                (width, depth), (-width, depth))
        vertices = tuple((center_x + x * cosine + z * sine,
                          rng.uniform(-2, 2),
                          center_z - x * sine + z * cosine)
                         for x, z in base)
        if index % 8 == 0:
            xz = vertices[index % 4][0], vertices[index % 4][2]
        else:
            xz = (center_x + rng.uniform(-width * 1.5, width * 1.5),
                  center_z + rng.uniform(-depth * 1.5, depth * 1.5))
        query = (xz[0], rng.uniform(-2, 2), xz[1])
        weights = bytes(rng.randrange(0, 256) for _ in range(4))
        other_vertices = tuple((x + 100, y, z + 100) for x, y, z in vertices)
        other_weights = bytes((1, 2, 3, 4))

        oracle._reset()
        polygon = _record(oracle, POLYGON, WEIGHTS, VERTICES, WEIGHTS,
                          vertices, weights)
        other = _record(oracle, OTHER, OTHER_WEIGHTS, OTHER_VERTICES,
                        OTHER_WEIGHTS, other_vertices, other_weights)
        cpu.mem_write(QUERY, struct.pack('<3f', *query))

        expected_mask = edge_crossing_mask(query, polygon, other)
        oracle.call(0x42D900, (QUERY, POLYGON, OTHER), instruction_limit=1000)
        actual_mask = cpu.reg_read(oracle.reg.UC_X86_REG_EAX)
        if actual_mask != expected_mask:
            raise AssertionError(f'case {index}: edge mask {actual_mask:#x} != '
                                 f'{expected_mask:#x}')
        mask_cases += 1

        cpu.mem_write(NORMAL, bytes(12))
        cpu.mem_write(POINT, bytes(12))
        cpu.mem_write(HEIGHT, bytes(4))
        inner_masks = []
        stage_normals = []
        def observe(machine, address, _size, _user):
            if address == 0x45C8D7:
                inner_masks.append(machine.reg_read(oracle.reg.UC_X86_REG_EAX))
            if address in (0x45C9B3, 0x45CA91, 0x45CB6F, 0x45CC47):
                stage_normals.append((hex(address), struct.unpack(
                    '<3f', machine.mem_read(NORMAL, 12))))
        hook = cpu.hook_add(UC_HOOK_CODE, observe)
        oracle.call(0x45C870,
                    (NORMAL, POINT, POLYGON, OTHER, QUERY, HEIGHT),
                    instruction_limit=10000)
        cpu.hook_del(hook)
        inner_mask = inner_masks[-1] if inner_masks else None
        accepted = cpu.reg_read(oracle.reg.UC_X86_REG_EAX) != 0
        actual = (struct.unpack('<3f', cpu.mem_read(NORMAL, 12)),
                  struct.unpack('<3f', cpu.mem_read(POINT, 12)),
                  struct.unpack('<f', cpu.mem_read(HEIGHT, 4))[0])
        expected = resolve_edge_contact(query, polygon, other)
        if accepted != expected.accepted:
            raise AssertionError(f'case {index}: acceptance {accepted} != '
                                 f'{expected.accepted} (mask {expected.edge_mask:#x})')
        wanted = (*expected.normal, *expected.point, expected.vertical_value)
        observed = (*actual[0], *actual[1], actual[2])
        for component, (a, b) in enumerate(zip(observed, wanted)):
            error = abs(a - b)
            maximum_output_error = max(maximum_output_error, error)
            if error > max(2e-5, abs(b) * 2e-6):
                raise AssertionError(
                    f'case {index}: output[{component}] {a} != {b}; '
                    f'native={observed!r} model={wanted!r} '
                    f'mask={expected.edge_mask:#x} inner={inner_mask!r} accepted={accepted} '
                    f'stages={stage_normals!r} '
                    f'vertices={vertices!r} weights={list(weights)}')
        contact_cases += int(accepted)

    return {'edge_mask_cases': mask_cases, 'contact_cases': count,
            'accepted_contacts': contact_cases,
            'maximum_absolute_output_error': maximum_output_error,
            'scope': 'direct 0x42d900 bitmask and 0x45c870 edge-contact output with supplied geometry records'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    parser.add_argument('--cases', type=int, default=256)
    args = parser.parse_args()
    print(json.dumps(compare(args.executable, args.cases)))


if __name__ == '__main__':
    main()
