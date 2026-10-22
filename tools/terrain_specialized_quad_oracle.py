"""Compare the specialized 0x54f0e0 projected-quad gate with mcity.exe."""
import argparse
import json
import math
import random
import struct

from unicorn import UC_HOOK_CODE

from client.collision_terrain import specialized_quad_projection_candidate
from tools.native_oracle import DynoOracle


OWNER = 0x71008000
GEOMETRY = OWNER + 0x1D00
CORNER_OFFSETS = (0x6FC, 0x808, 0x914, 0xA20)


def cases(count):
    rng = random.Random(0x54F0E0)
    fixed = ((0., 0.), (2., 0.), (0., 3.), (2., 3.), (6., 0.))
    for shift_x, shift_z in fixed[:count]:
        matrix = (1., 0., 0., 0., 1., 0., 0., 0., 1.)
        corners = ((shift_x - 2., 0., shift_z - 3.),
                   (shift_x - 2., 0., shift_z + 3.),
                   (shift_x + 2., 0., shift_z + 3.),
                   (shift_x + 2., 0., shift_z - 3.))
        yield (0., 0.), (0., 0., 0.), matrix, corners, .25
    for index in range(max(0, count - len(fixed))):
        angle = (0., .23, -.51, .89)[index % 4]
        c, s = math.cos(angle), math.sin(angle)
        matrix = (c, 0., -s, 0., 1., 0., s, 0., c)
        shift_x, shift_z = rng.uniform(-6., 6.), rng.uniform(-6., 6.)
        corners = ((shift_x - 2., 0., shift_z - 3.),
                   (shift_x - 2., 0., shift_z + 3.),
                   (shift_x + 2., 0., shift_z + 3.),
                   (shift_x + 2., 0., shift_z - 3.))
        point = (rng.uniform(-5., 5.), rng.uniform(-5., 5.))
        position = (rng.uniform(-2., 2.), 0., rng.uniform(-2., 2.))
        bound = rng.uniform(.05, .8)
        yield point, position, matrix, corners, bound


def compare(executable, count=64):
    oracle = DynoOracle(executable)
    cpu, reg = oracle.cpu, oracle.reg
    calls = []
    transformed = []

    def intercept(machine, address, _size, _user):
        if address == 0x54F193:
            ebp = machine.reg_read(reg.UC_X86_REG_EBP)
            values = struct.unpack('<12f', machine.mem_read(ebp - 0x38, 48))
            transformed.append(tuple(values[i:i + 3]
                                     for i in range(0, 12, 3)))
            return
        if address != 0x54F2A0:
            return
        sp = machine.reg_read(reg.UC_X86_REG_ESP)
        ret = struct.unpack('<I', machine.mem_read(sp, 4))[0]
        owner, corners_address, bound_bits = struct.unpack(
            '<3I', machine.mem_read(sp + 4, 12))
        corners = struct.unpack('<12f', machine.mem_read(corners_address, 48))
        corners = tuple(corners[i:i + 3] for i in range(0, 12, 3))
        bound = struct.unpack('<f', struct.pack('<I', bound_bits))[0]
        calls.append((owner, corners, bound))
        machine.reg_write(reg.UC_X86_REG_EAX, 1)
        machine.reg_write(reg.UC_X86_REG_ESP, sp + 4)
        machine.reg_write(reg.UC_X86_REG_EIP, ret)

    cpu.hook_add(UC_HOOK_CODE, intercept)
    delegated = rejected = 0
    for index, (projected, position, matrix, corners, bound) in enumerate(cases(count)):
        image = bytearray(0x1E40)
        struct.pack_into('<3f', image, 8, position[0], position[1], position[2])
        image[6] = 1
        struct.pack_into('<9f', image, 0x78, *matrix)
        for offset, corner in zip(CORNER_OFFSETS, corners):
            struct.pack_into('<3f', image, offset, *corner)
        struct.pack_into('<I', image, 0x1C94, GEOMETRY)
        struct.pack_into('<2f', image, 0x1D00 + 0x11C, bound, bound + .2)
        struct.pack_into('<f', image, 8, projected[0])
        struct.pack_into('<f', image, 0x10, projected[1])
        cpu.mem_write(OWNER, bytes(image))
        calls.clear()
        transformed.clear()
        oracle.call(0x54F0E0, (OWNER,), instruction_limit=500_000)
        actual = cpu.reg_read(reg.UC_X86_REG_EAX) != 0
        candidate = specialized_quad_projection_candidate(
            projected, corners, matrix,
            (projected[0], position[1], projected[1]), bound, bound + .2)
        if len(transformed) != 1:
            raise AssertionError(f'case {index}: transform output missing')
        for original_vertex, expected_vertex in zip(
                transformed[0], candidate.transformed_vertices):
            if any(abs(a-b) > max(2e-5, abs(a)*2e-6)
                   for a, b in zip(original_vertex, expected_vertex)):
                raise AssertionError(f'case {index}: transformed point differs: '
                                     f'{original_vertex!r} != {expected_vertex!r}')
        if candidate.intersects != bool(calls):
            raise AssertionError(f'case {index}: translated projection gate '
                                 f'{candidate.intersects} != delegation {bool(calls)}')
        if calls:
            if len(calls) != 1 or calls[0][0] != OWNER:
                raise AssertionError(f'case {index}: unexpected inner calls {calls!r}')
            _, world_corners, actual_bound = calls[0]
            expected_gate = candidate.intersects
            if not expected_gate:
                raise AssertionError(f'case {index}: caller delegated outside point')
            for original_vertex, forwarded_vertex in zip(
                    world_corners, candidate.transformed_vertices):
                if any(abs(a-b) > max(2e-5, abs(a)*2e-6)
                       for a, b in zip(original_vertex, forwarded_vertex)):
                    raise AssertionError(f'case {index}: inner worker points changed')
            expected_bound = candidate.forwarded_extent
            if abs(actual_bound - expected_bound) > max(1e-6, abs(expected_bound) * 1e-6):
                raise AssertionError(f'case {index}: forwarded bound {actual_bound} != {expected_bound}')
            if not actual:
                raise AssertionError(f'case {index}: delegated true result was lost')
            delegated += 1
        else:
            if actual:
                raise AssertionError(f'case {index}: accepted without inner collision')
            rejected += 1
    return {'entry': '0x54f0e0', 'cases': count, 'delegated': delegated,
            'projected_rejections': rejected,
            'scope': 'four-point mode-6 transform and projected XZ gate; delegated result with inner 0x54f2a0 stubbed'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    parser.add_argument('--cases', type=int, default=64)
    args = parser.parse_args()
    print(json.dumps(compare(args.executable, args.cases)))
