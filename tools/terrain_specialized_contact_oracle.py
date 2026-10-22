"""Compare 0x54f2a0's selected four-corner contacts with mcity.exe."""
import argparse
import json
import random
import struct

from unicorn import UC_HOOK_CODE

from client.collision_terrain import (sample_specialized_quad_heights,
                                      specialized_quad_contact_selection,
                                      specialized_quad_response_axes,
                                      specialized_quad_response_dynamics)
from tools.native_oracle import DynoOracle
from tools.support_correction_oracle import _install_world, _make_world
from tools.track_surface_cases import fixture


OWNER = 0x71008000
POINTS = 0x7100A000
GEOMETRY = OWNER + 0x1D00
VERTICES = ((6., 0., 6.), (6., 0., 10.),
            (10., 0., 10.), (10., 0., 6.))
EXTENT = 0.25
POSITION = (7., .5, 7.)
LINEAR_VELOCITY = (0., -.4, 0.)
ANGULAR_TURN_VELOCITY = (.01, .02, .03)
RESPONSE_GEOMETRY = {0x20: 10., 0x28: 1., 0x38: .1, 0xFC: .1,
                     0x104: .2, 0x114: .3, 0x118: .4}
RESPONSE_PARAMETERS = {0x18CC: .8, 0x18D4: .9, 0x18DC: .7, 0x18E0: .5,
                       0x18E8: .6, 0xD18: .1, 0xD1C: .2,
                       0xD20: .3, 0xD24: .4}


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
    maximum_axis_error = 0.0
    maximum_dynamics_error = 0.0
    selected_cases = 0
    rejected_cases = 0
    for case_index, offsets in enumerate(_cases(count)):
        height_shift = (-.2, -.05, 0., .1, .2)[case_index % 5]
        points = tuple((x, height_shift, z) for x, _y, z in VERTICES)
        extent = EXTENT
        sampling = sample_specialized_quad_heights(
            world, points, seed, normal, origin, extent)
        if not sampling.candidate.accepted:
            raise AssertionError('accepted-contact fixture failed its height gate')
        gain = f32(.75 + (case_index % 17) * .03)
        response_geometry = dict(RESPONSE_GEOMETRY)
        for offset in (0x38, 0xFC, 0x104, 0x114, 0x118):
            response_geometry[offset] = f32(response_geometry[offset] * gain)
        response_parameters = dict(RESPONSE_PARAMETERS)
        for offset in (0x18CC, 0x18D4, 0x18DC, 0x18E0, 0x18E8):
            response_parameters[offset] = f32(response_parameters[offset] * gain)
        for offset in (0xD18, 0xD1C, 0xD20, 0xD24):
            response_parameters[offset] = f32(response_parameters[offset] +
                                               (gain - 1.) * .1)
        expected = specialized_quad_contact_selection(
            points, sampling.normals, POSITION, LINEAR_VELOCITY,
            ANGULAR_TURN_VELOCITY, (0., 0., 0.),
            (1., 0., 0., 0., 1., 0., 0., 0., 1.), offsets,
            sampling.candidate.minimum_gap, extent,
            sampled_heights=sampling.candidate.heights)
        image = bytearray(0x1E40)
        struct.pack_into('<I', image, 0x1C94, GEOMETRY)
        struct.pack_into('<3f', image, 0x328, *normal)
        struct.pack_into('<3f', image, 0x340, *origin)
        struct.pack_into('<9f', image, 0x78,
                         1., 0., 0., 0., 1., 0., 0., 0., 1.)
        struct.pack_into('<3f', image, 8, *POSITION)
        struct.pack_into('<3f', image, 0x14, *LINEAR_VELOCITY)
        struct.pack_into('<3f', image, 0x38, *ANGULAR_TURN_VELOCITY)
        struct.pack_into('<f', image, 0x7C, .2)
        struct.pack_into('<3f', image, 0x84, .2, .3, .4)
        struct.pack_into('<f', image, 0x94, .4)
        struct.pack_into('<9f', image, 0x9C,
                         1., 0., 0., 0., 1., 0., 0., 0., 1.)
        struct.pack_into('<f', image, 0xD0, .5)
        struct.pack_into('<f', image, 0x18F4, .05)
        struct.pack_into('<I', image, 0x350, 1)
        struct.pack_into('<3f', image, 0x18FC, .2, .2, .15)
        for offset, value in response_parameters.items():
            struct.pack_into('<f', image, offset, value)
        image[0x370:0x370 + 0x44] = seed[:0x44]
        for index, offset in enumerate(offsets):
            struct.pack_into('<f', image, 0x6EC + index * 0x10C, offset)
        cpu.mem_write(OWNER, bytes(image))
        geometry = bytearray(0x120)
        for offset, value in response_geometry.items():
            struct.pack_into('<f', geometry, offset, value)
        cpu.mem_write(GEOMETRY, bytes(geometry))
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
            axes = specialized_quad_response_axes(
                expected, (1., 0., 0., 0., 1., 0., 0., 0., 1.),
                (.2, .3, .4), (7., .5, 7.), (.2, .3, .4), .5,
                .05, -.2, .2, .15)
            actual_axes = tuple(struct.unpack('<f', cpu.mem_read(OWNER + offset, 4))[0]
                                for offset in (0xC00, 0xC04, 0xBFC, 0xBF4, 0xBF8))
            expected_axes = (axes.yaw_correction, axes.pitch_correction,
                             axes.penetration, axes.roll_error, axes.pitch_error)
            for axis, (got, wanted) in enumerate(zip(actual_axes, expected_axes)):
                error = abs(got - wanted)
                maximum_axis_error = max(maximum_axis_error, error)
                if error > max(2e-5, abs(got) * 2e-6):
                    raise AssertionError(
                        f'case {case_index} response field {axis}: '
                        f'original {got} != translated {wanted}')
            dynamics = specialized_quad_response_dynamics(
                expected, axes, sampling.candidate.minimum_gap, POSITION,
                LINEAR_VELOCITY, ANGULAR_TURN_VELOCITY,
                struct.unpack_from('<9f', image, 0x9C),
                struct.unpack_from('<9f', image, 0x78),
                response_geometry, response_parameters)
            for label, offset, wanted in (
                    ('position', 8, dynamics.position),
                    ('linear velocity', 0x14, dynamics.linear_velocity),
                    ('angular response', 0x38, dynamics.angular_turn_velocity)):
                actual = struct.unpack('<3f', cpu.mem_read(OWNER + offset, 12))
                for axis, (got, value) in enumerate(zip(actual, wanted)):
                    error = abs(got - value)
                    maximum_dynamics_error = max(maximum_dynamics_error, error)
                    if error > max(3e-5, abs(got) * 3e-6):
                        raise AssertionError(
                            f'case {case_index} {label}[{axis}]: original {got} '
                            f'!= translated {value}; actual={actual!r} '
                            f'local={dynamics.local_before_response!r} '
                            f'corrected={dynamics.local_after_response!r}')
            actual_status = struct.unpack('<I', cpu.mem_read(OWNER + 0x350, 4))[0]
            wanted_status = 0 if dynamics.contact_state_cleared else 1
            if actual_status != wanted_status:
                raise AssertionError(
                    f'case {case_index} contact reset: original {actual_status} '
                    f'!= translated {wanted_status}')
        else:
            rejected_cases += 1
            if captured:
                raise AssertionError(f'case {case_index}: rejected candidate entered response')
    return {'entry': '0x54f2a0', 'cases': count + 7,
            'contact_selected': selected_cases, 'motion_rejected': rejected_cases,
            'maximum_selected_point_error': maximum,
            'maximum_response_axis_error': maximum_axis_error,
            'maximum_response_dynamics_error': maximum_dynamics_error,
            'scope': 'accepted height gate, four-corner motion filter, contact-normal projections, suspension angular response and inward normal-velocity correction; original x86 execution'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    parser.add_argument('--cases', type=int, default=256)
    args = parser.parse_args()
    print(json.dumps(compare(args.executable, args.cases)))
