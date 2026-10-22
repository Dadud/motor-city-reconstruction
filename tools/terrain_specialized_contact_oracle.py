"""Compare 0x54f2a0's selected four-corner contacts with mcity.exe."""
import argparse
import json
import random
import struct

from unicorn import UC_HOOK_CODE

from client.collision_terrain import (sample_specialized_quad_heights,
                                      specialized_quad_contact_selection)
from tools.native_oracle import DynoOracle
from tools.support_correction_oracle import _install_world, _make_world
from tools.track_surface_cases import fixture


OWNER = 0x71008000
POINTS = 0x7100A000
GEOMETRY = OWNER + 0x1D00
VERTICES = ((6., 0., 6.), (6., 0., 10.),
            (10., 0., 10.), (10., 0., 6.))
EXTENT = 0.25


def _cases(count):
    yield (0., 0., 0., 0.)
    yield (-.5, 0., 0., 0.)
    yield (-.5, -.5, 0., 0.)
    yield (-.5, -.5, -.5, 0.)
    yield (-.5, -.5, -.5, -.5)
    boundary = f32(((-0.3065625 * 0.03125) - EXTENT))
    yield (boundary - 1e-4,) * 4
    yield (boundary + 1e-4,) * 4
    rng = random.Random(0x54F2A0C)
    choices = (-.5, -.3, -.25, -.1, 0., .1, .4)
    for _ in range(count):
        yield tuple(rng.choice(choices) for _ in range(4))


def f32(value):
    return struct.unpack('<f', struct.pack('<f', value))[0]


def compare(executable, count=256):
    if type(count) is not int or count < 1:
        raise ValueError('case count must be a positive integer')
    arena, root, seed = fixture(2, 0, 0, 0, 7, 8, 8, 1)
    world = _make_world(arena, root)
    normal, origin = (0., 1., 0.), (0., 0., 0.)
    oracle = DynoOracle(executable)
    cpu = oracle.cpu
    _install_world(oracle, arena, root)
    captured = []

    def trace(machine, address, _size, _user):
        if address == 0x459E30:
            esp = machine.reg_read(oracle.reg.UC_X86_REG_ESP)
            _out, points = struct.unpack('<II', machine.mem_read(esp + 4, 8))
            captured.append(struct.unpack('<9f', machine.mem_read(points, 36)))

    cpu.hook_add(UC_HOOK_CODE, trace)
    maximum = 0.0
    selected_cases = 0
    rejected_cases = 0
    for case_index, offsets in enumerate(_cases(count)):
        points = VERTICES
        extent = EXTENT
        sampling = sample_specialized_quad_heights(
            world, points, seed, normal, origin, extent)
        if not sampling.candidate.accepted:
            raise AssertionError('accepted-contact fixture failed its height gate')
        expected = specialized_quad_contact_selection(
            points, sampling.normals, (0., 0., 0.), (0., 0., 0.),
            (0., 0., 0.), (0., 0., 0.),
            (1., 0., 0., 0., 1., 0., 0., 0., 1.), offsets,
            sampling.candidate.minimum_gap, extent)
        image = bytearray(0x1E40)
        struct.pack_into('<I', image, 0x1C94, GEOMETRY)
        struct.pack_into('<3f', image, 0x328, *normal)
        struct.pack_into('<3f', image, 0x340, *origin)
        struct.pack_into('<9f', image, 0x78,
                         1., 0., 0., 0., 1., 0., 0., 0., 1.)
        image[0x370:0x370 + 0x44] = seed[:0x44]
        for index, offset in enumerate(offsets):
            struct.pack_into('<f', image, 0x6EC + index * 0x10C, offset)
        cpu.mem_write(OWNER, bytes(image))
        cpu.mem_write(POINTS, struct.pack('<12f',
                                         *(value for point in points for value in point)))
        captured.clear()
        extent_bits = struct.unpack('<I', struct.pack('<f', extent))[0]
        oracle.call(0x54F2A0, (OWNER, POINTS, extent_bits),
                    instruction_limit=1_000_000)
        actual_return = cpu.reg_read(oracle.reg.UC_X86_REG_EAX)
        if bool(actual_return) != expected.candidate_accepted:
            raise AssertionError(
                f'case {case_index}: return {actual_return}, expected '
                f'{expected.candidate_accepted}; offsets={offsets!r} '
                f'gaps={expected.predicted_gaps!r}')
        if expected.candidate_accepted:
            selected_cases += 1
            if len(captured) != 2:
                raise AssertionError(f'case {case_index}: expected two normal calls, got {len(captured)}')
            # The worker sends adjusted owner corners to its first normal
            # helper call, followed by sampled plane points for the second.
            wanted_arrays = (expected.adjusted_points, expected.source_points)
            for call_index, (got_flat, wanted_points) in enumerate(zip(captured, wanted_arrays)):
                wanted_flat = tuple(value for point in wanted_points for value in point)
                for axis, (got, wanted) in enumerate(zip(got_flat, wanted_flat)):
                    error = abs(got - wanted)
                    maximum = max(maximum, error)
                    if error > max(2e-5, abs(got) * 2e-6):
                        raise AssertionError(
                            f'case {case_index} call {call_index} float {axis}: '
                            f'original {got} != translated {wanted}')
        else:
            rejected_cases += 1
            if captured:
                raise AssertionError(f'case {case_index}: rejected candidate entered response')
    return {'entry': '0x54f2a0', 'cases': count + 7,
            'contact_selected': selected_cases, 'motion_rejected': rejected_cases,
            'maximum_selected_point_error': maximum,
            'scope': 'accepted height gate, four-corner motion filter and the two point arrays passed to 0x459e30; original x86 execution'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    parser.add_argument('--cases', type=int, default=256)
    args = parser.parse_args()
    print(json.dumps(compare(args.executable, args.cases)))
