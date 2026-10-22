"""Compare 0x45a320's three-vertex motion gate across varied body states."""
import argparse
import json
import math
import random
import struct

from unicorn import UC_HOOK_CODE

from client.collision_terrain import (sample_triangle_candidate_heights,
                                     terrain_impact_response,
                                     terrain_contact_velocity_gate)
from tools.native_oracle import DynoOracle
from tools.support_correction_oracle import _install_world, _make_world
from tools.track_surface_cases import fixture


OWNER = 0x71008000
TABLE = 0x88C9D4
IDENTITY = (1., 0., 0., 0., 1., 0., 0., 0., 1.)
VERTICES = ((6., 0., 6.), (6., 0., 10.), (10., 0., 6.))


def body_states(count):
    rng = random.Random(0x45A320)
    for index in range(count):
        angle = (0., .2, .7, 1.1)[index % 4]
        cosine, sine = math.cos(angle), math.sin(angle)
        matrix = (cosine, 0., -sine, 0., 1., 0., sine, 0., cosine)
        linear = (rng.uniform(-3., 3.), rng.uniform(-5., 5.),
                  rng.uniform(-3., 3.))
        angular = tuple(rng.uniform(-.6, .6) for _ in range(3))
        center = tuple(rng.uniform(-.8, .8) for _ in range(3))
        yield linear, angular, center, matrix


def compare(executable, count=64):
    arena, root, seed = fixture(2, 0, 0, 0, 7, 8, 8, 1)
    world = _make_world(arena, root)
    plane_normal, plane_point = (0., 1., 0.), (0., 0., 0.)
    sampling = sample_triangle_candidate_heights(world, VERTICES, seed,
                                                 plane_normal, plane_point)
    oracle = DynoOracle(executable)
    cpu = oracle.cpu
    _install_world(oracle, arena, root)
    cpu.mem_write(TABLE, struct.pack('<36I', *([0, 1, 2] * 12)))
    addresses = (0x42E760, 0x42DC50, 0x459E30, 0x457550)
    counts = {address: 0 for address in addresses}
    response_inputs = []

    def trace(machine, address, _size, _user):
        if address in counts:
            counts[address] += 1
        if address == 0x457550:
            sp = machine.reg_read(oracle.reg.UC_X86_REG_ESP)
            body, normal_pointer, threshold_bits, sliding_bits = struct.unpack(
                '<4I', machine.mem_read(sp + 4, 16))
            normal = struct.unpack('<3f', machine.mem_read(normal_pointer, 12))
            threshold = struct.unpack('<f', struct.pack('<I', threshold_bits))[0]
            sliding = struct.unpack('<f', struct.pack('<I', sliding_bits))[0]
            response_inputs.append((body, normal, threshold, sliding))

    cpu.hook_add(UC_HOOK_CODE, trace)
    accepted = rejected = 0

    for case, (linear, angular, center, matrix) in enumerate(body_states(count)):
        image = bytearray(0xA00)
        struct.pack_into('<3f', image, 8, 8., 0., 8.)
        struct.pack_into('<3f', image, 0x14, *linear)
        struct.pack_into('<3f', image, 0x38, *angular)
        struct.pack_into('<3f', image, 0x5c, *center)
        struct.pack_into('<9f', image, 0x78, *matrix)
        struct.pack_into('<f', image, 0x50, 0.)  # no response impulse mutation
        struct.pack_into('<I', image, 0xdc, 0)
        struct.pack_into('<f', image, 0x318, 1.)
        struct.pack_into('<3f', image, 0x328, *plane_normal)
        struct.pack_into('<3f', image, 0x340, *plane_point)
        struct.pack_into('<I', image, 0x354, 0)
        struct.pack_into('<I', image, 0x404, 0)
        struct.pack_into('<9f', image, 0x1e8,
                         *(value for vertex in VERTICES for value in vertex))
        image[0x370:0x370 + 0x44] = seed[:0x44]
        cpu.mem_write(OWNER, bytes(image))
        before = bytes(cpu.mem_read(OWNER, len(image)))
        expected = terrain_contact_velocity_gate(
            VERTICES, sampling.normals, (8., 0., 8.), linear, angular, center,
            matrix, sampling.candidate.minimum_gap)
        for address in counts:
            counts[address] = 0
        response_inputs.clear()
        oracle.call(0x45A320, (OWNER,), instruction_limit=2_000_000)
        actual = cpu.reg_read(oracle.reg.UC_X86_REG_EAX) != 0
        if actual != expected.candidate_accepted:
            raise AssertionError(f'case {case}: original={actual}, '
                                 f'Python={expected.candidate_accepted}, '
                                 f'projections={expected.point_velocity_dots!r}')
        expected_calls = (3, 3, 2, 1) if actual else (3, 3, 0, 0)
        observed_calls = tuple(counts[address] for address in addresses)
        if observed_calls != expected_calls:
            raise AssertionError(f'case {case}: helper path {observed_calls!r} '
                                 f'!= {expected_calls!r}')
        after = bytes(cpu.mem_read(OWNER, len(image)))
        if actual:
            if len(response_inputs) != 1 or response_inputs[0][0] != OWNER:
                raise AssertionError(f'case {case}: missing response inputs')
            _, normal, threshold, sliding = response_inputs[0]
            # The outer caller first removes velocity into its object plane,
            # then retains only angular rate along that plane normal. The
            # supplied impact helper runs after these caller-side corrections.
            plane_speed = sum(linear[i] * plane_normal[i] for i in range(3))
            corrected_velocity = tuple(linear[i] - min(plane_speed, 0.) *
                                       plane_normal[i] for i in range(3))
            corrected_angular = tuple(angular[i] if plane_normal[i] != 0.
                                      else 0. for i in range(3))
            response = terrain_impact_response(corrected_velocity,
                                               corrected_angular, 0., normal,
                                               threshold, sliding)
            expected_velocity = response.linear_velocity
            expected_angular = response.angular_turn_velocity
            actual_velocity = struct.unpack_from('<3f', after, 0x14)
            actual_angular = struct.unpack_from('<3f', after, 0x38)
            if any(abs(a-b) > max(3e-5, abs(a)*3e-6)
                   for a, b in zip((*actual_velocity, *actual_angular),
                                   (*expected_velocity, *expected_angular))):
                raise AssertionError(f'case {case}: accepted response differs; '
                                     f'input_velocity={linear!r}, input_angular={angular!r}, '
                                     f'input={response_inputs[0]!r}, gravity={struct.unpack_from("<f",image,0x50)[0]}, '
                                     f'actual={actual_velocity!r}/{actual_angular!r}, '
                                     f'expected={expected_velocity!r}/{expected_angular!r}')
        elif after != before:
            changed = [offset for offset, (left, right) in enumerate(zip(before, after))
                       if left != right]
            raise AssertionError(f'case {case}: rejected candidate mutated body at {changed[:20]!r}')
        accepted += int(actual)
        rejected += int(not actual)

    return {'entry': '0x45a320', 'cases': accepted + rejected,
            'motion_gate_accepted': accepted, 'motion_gate_rejected': rejected,
            'scope': 'three-vertex point-velocity gate and caller-side plane velocity/rate corrections; varied linear/angular motion, COM and orientation'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    parser.add_argument('--cases', type=int, default=64)
    args = parser.parse_args()
    print(json.dumps(compare(args.executable, args.cases)))
