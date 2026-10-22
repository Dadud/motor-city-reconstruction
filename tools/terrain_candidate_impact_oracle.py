"""Trace one accepted 0x45a320 candidate through its surface response helper."""
import argparse
import json
import random
import struct

from unicorn import UC_HOOK_CODE

from client.collision_terrain import (sample_triangle_candidate_heights,
                                     terrain_contact_velocity_gate,
                                     terrain_impact_response,
                                     terrain_response_normal)
from tools.native_oracle import DynoOracle
from tools.support_correction_oracle import _install_world, _make_world
from tools.track_surface_cases import fixture


OWNER = 0x71008000
TABLE = 0x88C9D4


def compare(executable, response_cases=128):
    arena, root, seed = fixture(2, 0, 0, 0, 7, 8, 8, 1)
    world = _make_world(arena, root)
    vertices = ((6., 0., 6.), (6., 0., 10.), (10., 0., 6.))
    object_normal = (0., 1., 0.)
    plane_point = (0., 0., 0.)
    identity = (1., 0., 0., 0., 1., 0., 0., 0., 1.)
    sampled = sample_triangle_candidate_heights(world, vertices, seed,
                                                object_normal, plane_point)
    if not sampled.candidate.accepted:
        raise AssertionError(f'candidate should pass height filter: {sampled.candidate!r}')
    settled_gate = terrain_contact_velocity_gate(
        vertices, sampled.normals, (8., 0., 8.), (1., 0., 0.),
        (0., 0., 0.), (0., 0., 0.), identity,
        sampled.candidate.minimum_gap)
    rising_gate = terrain_contact_velocity_gate(
        vertices, sampled.normals, (8., 0., 8.), (0., 4., 0.),
        (0., 0., 0.), (0., 0., 0.), identity,
        sampled.candidate.minimum_gap)
    if not settled_gate.candidate_accepted or rising_gate.candidate_accepted:
        raise AssertionError('Python motion-gate fixtures do not separate contact states')

    oracle = DynoOracle(executable)
    cpu = oracle.cpu
    _install_world(oracle, arena, root)
    cpu.mem_write(TABLE, struct.pack('<36I', *([0, 1, 2] * 12)))
    image = bytearray(0xA00)
    struct.pack_into('<3f', image, 8, 8., 0., 8.)
    struct.pack_into('<3f', image, 0x14, 1., 0., 0.)
    struct.pack_into('<3f', image, 0x38, 0., 0., 0.)
    struct.pack_into('<f', image, 0x50, 1.)
    struct.pack_into('<I', image, 0xdc, 0)
    struct.pack_into('<3f', image, 0x318, 1., 0., 0.)
    struct.pack_into('<3f', image, 0x328, *object_normal)
    struct.pack_into('<3f', image, 0x340, *plane_point)
    struct.pack_into('<9f', image, 0x78, *identity)
    struct.pack_into('<I', image, 0x354, 0)
    struct.pack_into('<I', image, 0x404, 0)
    struct.pack_into('<9f', image, 0x1e8, *(v for vertex in vertices for v in vertex))
    image[0x370:0x370 + 0x44] = seed[:0x44]
    cpu.mem_write(OWNER, bytes(image))
    entries = []
    counts = {0x42E760: 0, 0x42DC50: 0, 0x459E30: 0, 0x457550: 0}

    def trace(machine, address, _size, _user):
        if address in counts:
            counts[address] += 1
        if address == 0x457550:
            sp = machine.reg_read(oracle.reg.UC_X86_REG_ESP)
            body, normal_pointer, threshold_bits, sliding_bits = struct.unpack(
                '<4I', machine.mem_read(sp + 4, 16))
            normal = struct.unpack('<3f', machine.mem_read(normal_pointer, 12))
            velocity = struct.unpack('<3f', machine.mem_read(body + 0x14, 12))
            angular = struct.unpack('<3f', machine.mem_read(body + 0x38, 12))
            entries.append((body, normal, struct.unpack('<f', struct.pack('<I', threshold_bits))[0],
                            struct.unpack('<f', struct.pack('<I', sliding_bits))[0],
                            velocity, angular))

    cpu.hook_add(UC_HOOK_CODE, trace)
    if type(response_cases) is not int or response_cases < 1:
        raise ValueError('response case count must be positive')
    rng = random.Random(0x45A320)
    maximum_response_error = 0.0
    velocities = [(1., 0., 0.)]
    angular_rates = [(0., 0., 0.)]
    for _ in range(response_cases - 1):
        velocities.append((rng.uniform(-3., 3.), rng.uniform(-.4, .0),
                           rng.uniform(-3., 3.)))
        angular_rates.append(tuple(rng.uniform(-.02, .02) for _ in range(3)))
    for case_index, (velocity, angular_rate) in enumerate(zip(velocities, angular_rates)):
        case_image = bytearray(image)
        struct.pack_into('<3f', case_image, 0x14, *velocity)
        struct.pack_into('<3f', case_image, 0x38, *angular_rate)
        cpu.mem_write(OWNER, bytes(case_image))
        entries.clear()
        counts.update({address: 0 for address in counts})
        before = bytes(cpu.mem_read(OWNER, len(case_image)))
        oracle.call(0x45A320, (OWNER,), instruction_limit=2_000_000)
        actual_return = cpu.reg_read(oracle.reg.UC_X86_REG_EAX)
        if actual_return != 1:
            raise AssertionError(f'case {case_index}: accepted candidate returned {actual_return}')
        if counts != {0x42E760: 3, 0x42DC50: 3, 0x459E30: 2, 0x457550: 1}:
            raise AssertionError(f'case {case_index}: unexpected accepted path {counts!r}')
        if len(entries) != 1 or entries[0][0] != OWNER:
            raise AssertionError(f'case {case_index}: could not capture response inputs {entries!r}')

        _, normal, threshold, sliding, response_velocity, response_angular = entries[0]
        wanted_normal = terrain_response_normal(vertices)
        if any(abs(a-b) > 2e-6 for a, b in zip(normal, wanted_normal)):
            raise AssertionError(f'case {case_index}: response normal {normal!r} != {wanted_normal!r}')
        response = terrain_impact_response(response_velocity, response_angular, 1.,
                                           normal, threshold, sliding)
        final_velocity = struct.unpack('<3f', cpu.mem_read(OWNER + 0x14, 12))
        final_angular = struct.unpack('<3f', cpu.mem_read(OWNER + 0x38, 12))
        final_impulse = struct.unpack('<3f', cpu.mem_read(OWNER + 0x3d8, 12))
        status = struct.unpack('<I', cpu.mem_read(OWNER + 0x3e4, 4))[0]
        if not response.applied or response.response_status != status:
            raise AssertionError(f'case {case_index}: translated response status differs')
        for actual, expected in zip((*final_velocity, *final_angular, *final_impulse),
                                    (*response.linear_velocity,
                                     *response.angular_turn_velocity,
                                     *response.tangential_impulse)):
            error = abs(actual - expected)
            maximum_response_error = max(maximum_response_error, error)
            if error > max(3e-5, abs(actual)*3e-6):
                raise AssertionError(
                    f'case {case_index}: full-caller response mismatch: {actual} != {expected}')
        before_body = bytearray(before)
        after_body = bytearray(cpu.mem_read(OWNER, len(case_image)))
        for start, end in ((0x14, 0x20), (0x38, 0x44), (0x3d8, 0x3e8)):
            before_body[start:end] = after_body[start:end]
        if before_body != after_body:
            raise AssertionError(f'case {case_index}: accepted candidate changed unmodeled fields')

    rising_image = bytearray(image)
    struct.pack_into('<3f', rising_image, 0x14, 0., 4., 0.)
    cpu.mem_write(OWNER, bytes(rising_image))
    counts.update({address: 0 for address in counts})
    before_rising = bytes(cpu.mem_read(OWNER, len(rising_image)))
    oracle.call(0x45A320, (OWNER,), instruction_limit=2_000_000)
    rising_return = cpu.reg_read(oracle.reg.UC_X86_REG_EAX)
    if rising_return != 0:
        raise AssertionError(f'rising body unexpectedly returned {rising_return}')
    if counts != {0x42E760: 3, 0x42DC50: 3, 0x459E30: 0, 0x457550: 0}:
        raise AssertionError(f'rising body did not stop at the motion gate: {counts!r}')
    if bytes(cpu.mem_read(OWNER, len(rising_image))) != before_rising:
        raise AssertionError('motion-gate rejection changed the supplied body')
    return {'entry': '0x45a320', 'response_cases': response_cases,
            'maximum_response_error': maximum_response_error,
            'response_normal': normal,
            'threshold': threshold, 'sliding': sliding,
            'response_status': status, 'candidate_calls': counts,
            'motion_gate_cases': 2,
            'scope': 'accepted response over varied linear/angular velocities plus rising-body rejection through the original caller'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    parser.add_argument('--cases', type=int, default=128)
    args = parser.parse_args()
    print(json.dumps(compare(args.executable, args.cases)))
