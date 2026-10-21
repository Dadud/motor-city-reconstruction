"""Compare recovered 0x45bfe0 contact-normal selection with mcity.exe."""
import argparse
import json
import math
import random
import struct

from client.collision_pair_geometry import OrientedCollisionBox, select_pair_contact_normal
from tools.collision_pair_geometry_oracle import axes, f32, put_floats
from tools.native_oracle import DynoOracle

OWNER, TARGET = 0x71000000, 0x71001000
SCRATCH = (0x0098D2A0, 0x0098D2A4, 0x0098D2CC)
NORMAL = 0x0098CDE0


def box_image(box):
    data = bytearray(0x100)
    struct.pack_into('<3f', data, 0x14, *box.center)
    for i, axis in enumerate(box.axes):
        struct.pack_into('<3f', data, 0x78 + i * 0x0c, *axis)
    struct.pack_into('<3f', data, 0xcc, *box.half_extents)
    return bytes(data)


def run_native(oracle, owner, target, projected, side):
    cpu, reg = oracle.cpu, oracle.reg
    oracle._reset()
    cpu.mem_write(OWNER, box_image(owner))
    cpu.mem_write(TARGET, box_image(target))
    for address, value in zip(SCRATCH, projected):
        put_floats(cpu, address, (f32(value),))
    stack = oracle.frame - 0x1000
    cpu.mem_write(stack, struct.pack('<4I', OWNER, TARGET, int(side), oracle.stop))
    call_at = oracle.stub
    cpu.mem_write(call_at, b'\xe8' + struct.pack('<i', 0x45bfe0 - (call_at + 5)) +
                  b'\x83\xc4\x0c\xc3')
    if hasattr(cpu, 'ctl_flush_tb'):
        cpu.ctl_flush_tb()
    cpu.reg_write(reg.UC_X86_REG_ESP, stack)
    cpu.reg_write(reg.UC_X86_REG_EBP, oracle.frame)
    oracle._run(call_at, oracle.stop, timeout=0, count=10000)
    return struct.unpack('<3f', cpu.mem_read(NORMAL, 12))


def cases(count):
    rng = random.Random(0x45BFE0)
    for index in range(count):
        owner = OrientedCollisionBox(
            tuple(f32(rng.uniform(-30, 30)) for _ in range(3)),
            axes(*(rng.uniform(-math.pi, math.pi) for _ in range(3))),
            tuple(f32(rng.uniform(1, 8)) for _ in range(3)))
        target = OrientedCollisionBox(
            tuple(f32(owner.center[i] + rng.uniform(-12, 12) if index % 2 == 0
                      else rng.uniform(-60, 60)) for i in range(3)),
            axes(*(rng.uniform(-math.pi, math.pi) for _ in range(3))),
            tuple(f32(rng.uniform(1, 8)) for _ in range(3)))
        projected = tuple(f32(rng.uniform(-8, 8)) for _ in range(3))
        yield owner, target, projected, index % 2


def compare(executable, count=256):
    oracle = DynoOracle(executable)
    maximum = 0.0
    branches = [0, 0]
    for index, (owner, target, projected, side) in enumerate(cases(count)):
        actual = run_native(oracle, owner, target, projected, side)
        expected = select_pair_contact_normal(owner, target, projected, side)
        branches[int(expected.near_center_branch)] += 1
        for component, (a, b) in enumerate(zip(actual, expected.normal)):
            error = abs(a - b)
            maximum = max(maximum, error)
            if error > 2e-5:
                raise AssertionError(f'case {index} normal[{component}] differs: {a} != {b}; '
                                     f'projected={projected}, side={side}, result={expected}')
    return {'entry': '0x45bfe0', 'cases': count, 'near_center': branches[1],
            'far_center': branches[0], 'maximum_absolute_float_error': maximum,
            'scope': 'direct original helper calls with explicit boxes and projection scratch'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    parser.add_argument('--cases', type=int, default=256)
    args = parser.parse_args()
    print(json.dumps(compare(args.executable, args.cases)))


if __name__ == '__main__':
    main()
