"""Compare the four-corner height gate in 0x54f2a0 with mcity.exe."""
import argparse
import json
import random
import struct

from unicorn import UC_HOOK_CODE

from client.collision_terrain import sample_specialized_quad_heights
from tools.native_oracle import DynoOracle
from tools.support_correction_oracle import _install_world, _make_world
from tools.track_surface_cases import fixture


OWNER = 0x71008000
POINTS = 0x7100A000
GEOMETRY = OWNER + 0x1D00
VERTICES = ((6., 1., 6.), (6., 1., 10.),
            (10., 1., 10.), (10., 1., 6.))


def compare(executable, case_count=64):
    if type(case_count) is not int or case_count < 1:
        raise ValueError('case count must be a positive integer')
    arena, root, seed = fixture(2, 0, 0, 0, 7, 8, 8, 1)
    world = _make_world(arena, root)
    normal, origin = (0., 1., 0.), (0., 0., 0.)
    oracle = DynoOracle(executable)
    cpu = oracle.cpu
    _install_world(oracle, arena, root)
    addresses = (0x42E760, 0x42DC50, 0x4B71A0,
                 0x457910, 0x459E30, 0x457550)
    counts = {address: 0 for address in addresses}
    aggregate_counts = {address: 0 for address in addresses}

    def trace(_machine, address, _size, _user):
        if address in counts:
            counts[address] += 1

    cpu.hook_add(UC_HOOK_CODE, trace)
    rng = random.Random(0x54F2A0)
    min_gap = float('inf')
    max_gap = float('-inf')
    fallback_heights = 0
    for case in range(case_count):
        heights = tuple(rng.choice((.5, .75, 1., 1.5, 3.)) for _ in range(4))
        xs = tuple(rng.uniform(5., 11.) for _ in range(4))
        zs = tuple(rng.uniform(5., 11.) for _ in range(4))
        points = tuple((xs[i], heights[i], zs[i]) for i in range(4))
        extent = rng.uniform(.1, .49)
        sampling = sample_specialized_quad_heights(
            world, points, seed, normal, origin, extent)
        candidate = sampling.candidate
        if candidate.accepted:
            raise AssertionError(f'case {case}: fixture should reject at height gate: '
                                 f'{candidate!r}')
        min_gap = min(min_gap, candidate.minimum_gap)
        max_gap = max(max_gap, candidate.minimum_gap)
        fallback_heights += sum(abs(gap) > .5 for gap in candidate.gaps)
        image = bytearray(0x1E40)
        struct.pack_into('<I', image, 0x1C94, GEOMETRY)
        struct.pack_into('<3f', image, 0x328, *normal)
        struct.pack_into('<3f', image, 0x340, *origin)
        image[0x370:0x370 + 0x44] = seed[:0x44]
        struct.pack_into('<6I', image, 0xC64,
                         *(0xA0 + i for i in range(6)))
        cpu.mem_write(OWNER, bytes(image))
        cpu.mem_write(POINTS, struct.pack('<12f',
                                         *(value for v in points for value in v)))
        for address in counts:
            counts[address] = 0
        extent_bits = struct.unpack('<I', struct.pack('<f', extent))[0]
        oracle.call(0x54F2A0, (OWNER, POINTS, extent_bits),
                    instruction_limit=1_000_000)
        actual = cpu.reg_read(oracle.reg.UC_X86_REG_EAX)
        if actual != 0:
            raise AssertionError(f'case {case}: original worker returned {actual}, '
                                 'expected height rejection')
        expected = {0x42E760: 4, 0x42DC50: 4,
                    0x4B71A0: 4 + sum(abs(gap) > .5 for gap in candidate.gaps),
                    0x457910: 0, 0x459E30: 0, 0x457550: 0}
        if counts != expected:
            raise AssertionError(f'case {case}: helper path {counts!r} != {expected!r}')
        for address, observed in counts.items():
            aggregate_counts[address] += observed
        after = bytes(cpu.mem_read(OWNER, len(image)))
        expected_image = bytearray(image)
        expected_image[0xC64:0xC64 + 24] = bytes(24)
        if after != bytes(expected_image):
            changed = [i for i, (a, b) in enumerate(zip(expected_image, after))
                       if a != b]
            raise AssertionError(f'case {case}: unexpected rejection writes at '
                                 f'{changed[:20]!r}')
    return {'entry': '0x54f2a0', 'cases': case_count,
            'height_rejected': case_count,
            'minimum_gap_range': (min_gap, max_gap),
            'surface_fallbacks': fallback_heights,
            'aggregate_helper_calls': {hex(address): count
                                       for address, count in aggregate_counts.items()},
            'cleared_record_bytes': 24,
            'scope': 'four-corner sampled/object-plane height gate; response phase not entered'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    parser.add_argument('--cases', type=int, default=64)
    args = parser.parse_args()
    print(json.dumps(compare(args.executable, args.cases)))
