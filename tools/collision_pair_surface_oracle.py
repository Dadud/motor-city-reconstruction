"""Compare the 0x459b90 vertex-to-plane response against mcity.exe."""
import argparse
import json
import math
import random
import struct

from client.body_constructor import construct_body
from client.collision_pair_surface import resolve_pair_surface
from client.geometry_transform import transform_vertices
from tools.native_oracle import DynoOracle


OWNER = 0x71008000
NORMAL = 0x7100A000
PLANE = 0x7100A100


def _bits(value):
    return struct.unpack('<I', struct.pack('<f', value))[0]


def _close(a, b, tolerance=3e-5):
    return (math.isnan(a) and math.isnan(b)) or abs(a-b) <= max(tolerance, abs(b)*3e-6)


def compare(executable, cases=128):
    if type(cases) is not int or cases < 1:
        raise ValueError('case count must be positive')
    oracle = DynoOracle(executable)
    cpu = oracle.cpu
    rng = random.Random(0x459B90)
    impacts = corrections = selected = 0
    maximum_float_error = 0.0
    for case in range(cases):
        body = bytearray(construct_body(bytes(0x2000), OWNER, 800.,
                                        (1.2, 1., .9), 0, 2))
        position = (rng.uniform(-.2, .2), rng.uniform(-.35, .15),
                    rng.uniform(-.2, .2))
        velocity_y = (rng.uniform(.2, 3.) if case % 4 == 0 else
                      -rng.uniform(.2, 3.))
        velocity = (rng.uniform(-.5, .5), velocity_y,
                    rng.uniform(-.5, .5))
        struct.pack_into('<3f', body, 8, *position)
        struct.pack_into('<3f', body, 0x14, *velocity)
        struct.pack_into('<3f', body, 0x38, *(rng.uniform(-.04, .04) for _ in range(3)))
        compact = case % 5 == 0
        struct.pack_into('<h', body, 0x3bc, 0 if compact else 1)
        struct.pack_into('<f', body, 0xc4, .5 if compact else 1.)
        local = tuple((rng.uniform(-.8, .8), -rng.uniform(.05, 1.2),
                       rng.uniform(-.8, .8)) for _ in range(22))
        struct.pack_into('<66f', body, 0xe0,
                         *(value for point in local for value in point))
        world_cache = transform_vertices(tuple(v for p in local for v in p),
                                         struct.unpack_from('<9f', body, 0x78),
                                         position)
        struct.pack_into('<66f', body, 0x1e8, *world_cache)
        normal = (0., 1., 0.)
        plane_point = (0., 0., 0.)
        max_distance = rng.uniform(.1, 1.2)
        max_height = -5. if case % 8 == 1 else rng.uniform(-.2, .8)
        threshold, sliding = .45, .2
        expected = resolve_pair_surface(bytes(body), OWNER, normal, plane_point,
                                        max_distance, threshold, sliding,
                                        max_height)

        oracle._reset()
        cpu.mem_write(OWNER, bytes(body))
        cpu.mem_write(NORMAL, struct.pack('<3f', *normal))
        cpu.mem_write(PLANE, struct.pack('<3f', *plane_point))
        oracle.call(0x459B90, (OWNER, NORMAL, PLANE, _bits(max_distance),
                               _bits(threshold), _bits(sliding),
                               _bits(max_height)), instruction_limit=1_000_000)
        native_return = bool(cpu.reg_read(oracle.reg.UC_X86_REG_EAX))
        actual = bytes(cpu.mem_read(OWNER, 0x408))
        if native_return != expected.collided:
            raise AssertionError(
                f'case {case}: return {native_return} != {expected.collided}; '
                f'selected={expected.selected_vertex}, penetration={expected.penetration}')
        impacts += int(native_return)
        selected += int(expected.selected_vertex is not None)
        corrections += int(expected.penetration > 0.)
        float_ranges = ((8, 0x14), (0x14, 0x20), (0x38, 0x44),
                        (0x1e8, 0x2f0), (0x3c8, 0x3e4), (0x3e8, 0x3f4))
        for offset in range(0x408):
            if any(start <= offset < end for start, end in float_ranges):
                continue
            if actual[offset] != expected.body_image[offset]:
                raise AssertionError(
                    f'case {case}: byte {offset:#x} {actual[offset]:#x} != '
                    f'{expected.body_image[offset]:#x}')
        for offset, length in ((8, 12), (0x14, 12), (0x38, 12),
                               (0x1e8, 0x108), (0x3c8, 0x1c), (0x3e8, 12)):
            values_a = struct.unpack('<'+'f'*(length//4), actual[offset:offset+length])
            values_b = struct.unpack('<'+'f'*(length//4), expected.body_image[offset:offset+length])
            for index, (a, b) in enumerate(zip(values_a, values_b)):
                error = abs(a-b)
                maximum_float_error = max(maximum_float_error, error)
                if not _close(a, b):
                    raise AssertionError(
                        f'case {case}: float at {offset + index*4:#x} {a} != {b}')
    return {'entry': '0x459b90', 'cases': cases,
            'selected_vertices': selected, 'impacts': impacts,
            'position_corrections': corrections,
            'maximum_float_error': maximum_float_error,
            'scope': 'original x86 execution; supplied plane, coefficients and body geometry'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    parser.add_argument('--cases', type=int, default=128)
    args = parser.parse_args()
    print(json.dumps(compare(args.executable, args.cases)))


if __name__ == '__main__':
    main()
