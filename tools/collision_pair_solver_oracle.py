"""Compare Python 0x45af30 pair resolution to direct original executions."""
import argparse
import json
import math
import random
import struct

from client.collision_pair_geometry import OrientedCollisionBox
from client.collision_pair_solver import CollisionPairBody, resolve_collision_pair
from tools.collision_pair_geometry_oracle import axes, f32
from tools.native_oracle import DynoOracle


OWNER, TARGET = 0x71000000, 0x71001000


def body_image(body):
    data = bytearray(0x500)
    box = body.box
    struct.pack_into('<B', data, 5, body.mode & 0xff)
    struct.pack_into('<3f', data, 8, *box.center)
    for index, axis in enumerate(box.axes):
        struct.pack_into('<3f', data, 0x78 + index * 0x0c, *axis)
    struct.pack_into('<f', data, 0x50, f32(body.mass))
    struct.pack_into('<f', data, 0x6c, f32(body.gate))
    struct.pack_into('<3f', data, 0xcc, *box.half_extents)
    struct.pack_into('<f', data, 0x3c0, f32(body.peer_gate))
    return bytes(data)


def run_native(oracle, owner, target):
    cpu, reg = oracle.cpu, oracle.reg
    oracle._reset()
    cpu.mem_write(OWNER, body_image(owner))
    cpu.mem_write(TARGET, body_image(target))
    stack = oracle.frame - 0x1000
    cpu.mem_write(stack, struct.pack('<3I', OWNER, TARGET, oracle.stop))
    call_at = oracle.stub
    cpu.mem_write(call_at, b'\xe8' + struct.pack('<i', 0x45af30 - (call_at + 5)) +
                  b'\x83\xc4\x08\xc3')
    if hasattr(cpu, 'ctl_flush_tb'):
        cpu.ctl_flush_tb()
    cpu.reg_write(reg.UC_X86_REG_ESP, stack)
    cpu.reg_write(reg.UC_X86_REG_EBP, oracle.frame)
    oracle._run(call_at, oracle.stop, timeout=0, count=2_000_000)
    return (cpu.reg_read(reg.UC_X86_REG_EAX),
            struct.unpack('<3f', cpu.mem_read(OWNER + 8, 12)),
            struct.unpack('<3f', cpu.mem_read(TARGET + 8, 12)))


def cases(count=64):
    rng = random.Random(0x45AF30)
    for index in range(count):
        if index < 16:
            orientation = ((1., 0., 0.), (0., 1., 0.), (0., 0., 1.))
            owner_center = (0., 0., 0.)
            target_center = (f32((index % 8) * .35), 0., 0.)
            extents = (1., 1., 1.)
            target_extents = (1., 1., 1.)
        else:
            orientation = axes(*(rng.uniform(-math.pi, math.pi) for _ in range(3)))
            target_orientation = axes(*(rng.uniform(-math.pi, math.pi) for _ in range(3)))
            owner_center = tuple(f32(rng.uniform(-.5, .5)) for _ in range(3))
            target_center = tuple(f32(owner_center[i] + rng.uniform(-1.8, 1.8))
                                  for i in range(3))
            extents = tuple(f32(rng.uniform(.5, 2)) for _ in range(3))
            target_extents = tuple(f32(rng.uniform(.5, 2)) for _ in range(3))
        if index < 16:
            target_orientation = orientation
        owner_mode = index % 4 in (1, 3)
        target_mode = index % 4 in (2, 3)
        owner = CollisionPairBody(
            OrientedCollisionBox(owner_center, orientation, extents),
            mass=f32(rng.uniform(100, 2000)), mode=int(owner_mode),
            gate=f32(rng.uniform(0, 1)), peer_gate=f32(rng.uniform(0, 1)))
        target = CollisionPairBody(
            OrientedCollisionBox(target_center, target_orientation, target_extents),
            mass=f32(rng.uniform(100, 2000)), mode=int(target_mode),
            gate=f32(rng.uniform(0, 1)), peer_gate=f32(rng.uniform(0, 1)))
        yield owner, target


def compare(executable, count=64):
    oracle = DynoOracle(executable)
    maximum = 0.0
    collided = 0
    steps = 0
    for index, (owner, target) in enumerate(cases(count)):
        native_hit, native_owner, native_target = run_native(oracle, owner, target)
        translated = resolve_collision_pair(owner, target)
        if native_hit != int(translated.collided):
            raise AssertionError(f'case {index} collision status differs: '
                                 f'{native_hit} vs {translated.collided}')
        for label, actual, expected in (
                ('owner position', native_owner, translated.owner.box.center),
                ('target position', native_target, translated.target.box.center)):
            for axis, (a, b) in enumerate(zip(actual, expected)):
                error = abs(a - b)
                maximum = max(maximum, error)
                if error > max(3e-5, abs(a) * 4e-6):
                    raise AssertionError(f'case {index} {label}[{axis}] differs: '
                                         f'{a} != {b}; steps={translated.correction_steps}')
        collided += int(native_hit != 0)
        steps += translated.correction_steps
    return {'entry': '0x45af30', 'cases': count, 'collided': collided,
            'python_correction_steps': steps, 'maximum_absolute_position_error': maximum,
            'scope': 'collision decision and position response; post-call transform-refresh outputs excluded'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    parser.add_argument('--cases', type=int, default=64)
    args = parser.parse_args()
    print(json.dumps(compare(args.executable, args.cases)))


if __name__ == '__main__':
    main()
