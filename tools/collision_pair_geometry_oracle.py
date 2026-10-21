"""Compare the translated 0x45b8e0 oriented-box point test to mcity.exe."""
import argparse
import math
import random
import struct
from pathlib import Path

from client.collision_pair_geometry import (OrientedCollisionBox,
                                            oriented_box_point_test)
from tools.native_oracle import DynoOracle


OWNER = 0x71000000
TARGET = OWNER + 0x1000
GLOBAL_MATRIX = 0x0098D2A8
GLOBAL_CENTER = 0x0098CD9C
GLOBAL_LOCAL_X = 0x0098D2A0
GLOBAL_LOCAL_Y = 0x0098D2A4
GLOBAL_LOCAL_Z = 0x0098D2CC
GLOBAL_DIRECTION = 0x0098CDE0
GLOBAL_WORLD_POINT = 0x0098CD90
GLOBAL_REVERSE_MATRIX = 0x0098CDB4
GLOBAL_REVERSE_CENTER = 0x0098CDA8


def f32(value):
    return struct.unpack('<f', struct.pack('<f', value))[0]


def put_floats(cpu, address, values):
    cpu.mem_write(address, struct.pack('<' + 'f' * len(values), *values))


def box_image(box):
    data = bytearray(0x100)
    struct.pack_into('<3f', data, 8, *box.center)
    for i, axis in enumerate(box.axes):
        struct.pack_into('<3f', data, 0x78 + i * 0x0c, *axis)
    struct.pack_into('<3f', data, 0xcc, *box.half_extents)
    return bytes(data)


def axes(yaw, pitch, roll):
    cy, sy = math.cos(yaw), math.sin(yaw)
    cp, sp = math.cos(pitch), math.sin(pitch)
    cr, sr = math.cos(roll), math.sin(roll)
    matrix = (
        (cy * cp, cy * sp * sr - sy * cr, cy * sp * cr + sy * sr),
        (sy * cp, sy * sp * sr + cy * cr, sy * sp * cr - cy * sr),
        (-sp, cp * sr, cp * cr),
    )
    return tuple(tuple(f32(x) for x in row) for row in matrix)


def dot(a, b):
    return f32(sum(a[i] * b[i] for i in range(3)))


def seed_native_scratch(cpu, owner, target):
    matrix = []
    for owner_axis in owner.axes:
        for target_axis, extent in zip(target.axes, target.half_extents):
            matrix.append(f32(dot(owner_axis, target_axis) * extent))
    put_floats(cpu, GLOBAL_MATRIX, matrix)
    delta = tuple(f32(target.center[i] - owner.center[i]) for i in range(3))
    put_floats(cpu, GLOBAL_CENTER,
               tuple(dot(axis, delta) for axis in owner.axes))


def run_native(oracle, owner, target, point):
    cpu, reg = oracle.cpu, oracle.reg
    oracle._reset()
    cpu.mem_write(OWNER, box_image(owner))
    cpu.mem_write(TARGET, box_image(target))
    seed_native_scratch(cpu, owner, target)
    stack = oracle.frame - 0x1000
    args = (OWNER, TARGET, *(struct.unpack('<I', struct.pack('<f', x))[0]
                             for x in point))
    cpu.mem_write(stack, struct.pack('<6I', *args, oracle.stop))
    call_at = oracle.stub
    code = b'\xe8' + struct.pack('<i', 0x45b8e0 - (call_at + 5))
    code += b'\x83\xc4\x14\xc3'
    cpu.mem_write(call_at, code)
    if hasattr(cpu, 'ctl_flush_tb'):
        cpu.ctl_flush_tb()
    cpu.reg_write(reg.UC_X86_REG_ESP, stack)
    cpu.reg_write(reg.UC_X86_REG_EBP, oracle.frame)
    oracle._run(call_at, oracle.stop, timeout=0, count=10000)
    inside = cpu.reg_read(reg.UC_X86_REG_EAX)
    projected = tuple(struct.unpack('<f', cpu.mem_read(address, 4))[0]
                      for address in (GLOBAL_LOCAL_X, GLOBAL_LOCAL_Y,
                                      GLOBAL_LOCAL_Z))
    direction = struct.unpack('<3f', cpu.mem_read(GLOBAL_DIRECTION, 12))
    contact = struct.unpack('<3f', cpu.mem_read(GLOBAL_WORLD_POINT, 12))
    return inside, projected, direction, contact


def seed_reverse_scratch(cpu, owner, target):
    matrix = []
    for owner_axis, extent in zip(owner.axes, owner.half_extents):
        for target_axis in target.axes:
            matrix.append(f32(dot(owner_axis, target_axis) * extent))
    put_floats(cpu, GLOBAL_REVERSE_MATRIX, matrix)
    delta = tuple(f32(target.center[i] - owner.center[i]) for i in range(3))
    put_floats(cpu, GLOBAL_REVERSE_CENTER,
               tuple(dot(axis, delta) for axis in target.axes))


def run_native_reverse(oracle, owner, target, point, entry):
    cpu, reg = oracle.cpu, oracle.reg
    oracle._reset()
    cpu.mem_write(OWNER, box_image(owner))
    cpu.mem_write(TARGET, box_image(target))
    seed_reverse_scratch(cpu, owner, target)
    stack = oracle.frame - 0x1000
    args = (OWNER, TARGET, *(struct.unpack('<I', struct.pack('<f', x))[0]
                             for x in point))
    cpu.mem_write(stack, struct.pack('<6I', *args, oracle.stop))
    call_at = oracle.stub
    code = b'\xe8' + struct.pack('<i', entry - (call_at + 5))
    code += b'\x83\xc4\x14\xc3'
    cpu.mem_write(call_at, code)
    if hasattr(cpu, 'ctl_flush_tb'):
        cpu.ctl_flush_tb()
    cpu.reg_write(reg.UC_X86_REG_ESP, stack)
    cpu.reg_write(reg.UC_X86_REG_EBP, oracle.frame)
    oracle._run(call_at, oracle.stop, timeout=0, count=10000)
    inside = cpu.reg_read(reg.UC_X86_REG_EAX)
    projected = tuple(struct.unpack('<f', cpu.mem_read(address, 4))[0]
                      for address in (GLOBAL_LOCAL_X, GLOBAL_LOCAL_Y,
                                      GLOBAL_LOCAL_Z))
    direction = struct.unpack('<3f', cpu.mem_read(GLOBAL_DIRECTION, 12))
    contact = struct.unpack('<3f', cpu.mem_read(GLOBAL_WORLD_POINT, 12))
    return inside, projected, direction, contact


def cases(count=192):
    rng = random.Random(0x45B8E0)
    for index in range(count):
        if index < 32:
            owner = OrientedCollisionBox((0, 0, 0),
                ((1, 0, 0), (0, 1, 0), (0, 0, 1)), (2, 2, 2))
            target = OrientedCollisionBox((0, 0, 0),
                ((1, 0, 0), (0, 1, 0), (0, 0, 1)), (1, 1, 1))
            probes = ((0, 0, 0), (1, 0, 0), (-1, 0, 0), (0, 1, 0),
                      (0, -1, 0), (0, 0, 1), (0, 0, -1), (1, 1, 1),
                      (1.5, -1.5, 1.5), (3, 0, 0), (0, 3, 0), (0, 0, -3))
            yield owner, target, tuple(f32(x) for x in probes[index % len(probes)])
            continue
        owner = OrientedCollisionBox(
            tuple(f32(rng.uniform(-2, 2) if index % 2 == 0 else
                      rng.uniform(-20, 20)) for _ in range(3)),
            axes(*(rng.uniform(-math.pi, math.pi) for _ in range(3))),
            tuple(f32(rng.uniform(20, 30) if index % 2 == 0 else
                      rng.uniform(0.5, 8)) for _ in range(3)))
        target = OrientedCollisionBox(
            tuple(f32(rng.uniform(-2, 2) if index % 2 == 0 else
                      rng.uniform(-20, 20)) for _ in range(3)),
            axes(*(rng.uniform(-math.pi, math.pi) for _ in range(3))),
            tuple(f32(rng.uniform(0.25, 5)) for _ in range(3)))
        point = tuple(f32(rng.uniform(-1.5, 1.5)) for _ in range(3))
        if index % 8 == 0:
            point = (0.0, 0.0, 0.0)
        yield owner, target, point


def reverse_cases(count=192):
    rng = random.Random(0x45BB7045BE10)
    probes = ((0, 0, 0), (1, 0, 0), (-1, 0, 0), (0, 1, 0),
              (0, -1, 0), (0, 0, 1), (0, 0, -1), (1, 1, 1),
              (1.5, -1.5, 1.5), (3, 0, 0), (0, 3, 0), (0, 0, -3))
    for index in range(count):
        if index < 48:
            owner = OrientedCollisionBox((0, 0, 0),
                ((1, 0, 0), (0, 1, 0), (0, 0, 1)), (1, 1, 1))
            target = OrientedCollisionBox((0, 0, 0),
                ((1, 0, 0), (0, 1, 0), (0, 0, 1)), (2, 2, 2))
            point = tuple(f32(x) for x in probes[index % len(probes)])
        else:
            owner = OrientedCollisionBox(
                tuple(f32(rng.uniform(-1, 1) if index % 2 == 0 else
                          rng.uniform(-20, 20)) for _ in range(3)),
                axes(*(rng.uniform(-math.pi, math.pi) for _ in range(3))),
                tuple(f32(rng.uniform(0.25, 2) if index % 2 == 0 else
                          rng.uniform(0.5, 8)) for _ in range(3)))
            target = OrientedCollisionBox(
                tuple(f32(rng.uniform(-1, 1) if index % 2 == 0 else
                          rng.uniform(-20, 20)) for _ in range(3)),
                axes(*(rng.uniform(-math.pi, math.pi) for _ in range(3))),
                tuple(f32(rng.uniform(10, 20) if index % 2 == 0 else
                          rng.uniform(0.25, 5)) for _ in range(3)))
            point = tuple(f32(rng.uniform(-1.5, 1.5)) for _ in range(3))
        yield owner, target, point, index % 2 == 0


def compare(executable, case_count=192):
    oracle = DynoOracle(executable)
    maximum_error = 0.0
    hits = 0
    for index, (owner, target, point) in enumerate(cases(case_count)):
        native_status, native_local, native_direction, native_contact = run_native(
            oracle, owner, target, point)
        translated = oriented_box_point_test(owner, target, point)
        if native_status != int(translated.inside):
            raise AssertionError(f'case {index} hit mismatch: {native_status} vs {translated}')
        comparisons = [(native_local, translated.owner_local_point,
                        'owner local point')]
        if translated.inside:
            comparisons.extend(((native_direction, translated.target_direction,
                                 'direction'),
                                (native_contact, translated.target_world_point,
                                 'world contact')))
        for actual, expected, label in comparisons:
            for component, (a, b) in enumerate(zip(actual, expected)):
                error = abs(a - b)
                maximum_error = max(maximum_error, error)
                if error > max(2e-5, abs(a) * 3e-6):
                    raise AssertionError(
                        f'case {index} {label}[{component}] differs: {a} vs {b}; '
                        f'point={point}, local={native_local}/{translated.owner_local_point}')
        hits += int(native_status != 0)
    return {'entry': '0x45b8e0', 'cases': case_count, 'hits': hits,
            'maximum_absolute_float_error': maximum_error,
            'scope': 'complete helper call with caller matrix/offset scratch supplied'}


def compare_reverse(executable, case_count=192):
    from client.collision_pair_geometry import (owner_point_contact_test,
                                                owner_point_direction_test)
    oracle = DynoOracle(executable)
    summary = {}
    for entry, label, translated_fn in (
            (0x45BB70, '0x45bb70', owner_point_direction_test),
            (0x45BE10, '0x45be10', owner_point_contact_test)):
        maximum_error = 0.0
        hits = 0
        for index, (owner, target, point, _direction_case) in enumerate(
                reverse_cases(case_count)):
            native_status, native_local, native_direction, native_contact = run_native_reverse(
                oracle, owner, target, point, entry)
            translated = translated_fn(owner, target, point)
            if native_status != int(translated.inside):
                raise AssertionError(f'{label} case {index} hit mismatch: {native_status} vs {translated}')
            comparisons = [(native_local, translated.target_local_point, 'target local point')]
            if translated.inside:
                comparisons.append((native_contact, translated.owner_world_point, 'owner world point'))
                if translated.owner_direction is not None:
                    comparisons.append((native_direction, translated.owner_direction, 'owner direction'))
                hits += 1
            for actual, expected, output in comparisons:
                for component, (a, b) in enumerate(zip(actual, expected)):
                    error = abs(a - b)
                    maximum_error = max(maximum_error, error)
                    if error > max(2e-5, abs(a) * 3e-6):
                        raise AssertionError(
                            f'{label} case {index} {output}[{component}] differs: {a} vs {b}')
        summary[label] = {'cases': case_count, 'hits': hits,
                          'maximum_absolute_float_error': maximum_error}
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', type=Path)
    parser.add_argument('--cases', type=int, default=192)
    parser.add_argument('--reverse', action='store_true',
                        help='compare sibling helpers 0x45bb70 and 0x45be10')
    args = parser.parse_args()
    print(compare_reverse(args.executable, args.cases) if args.reverse else
          compare(args.executable, args.cases))


if __name__ == '__main__':
    main()
