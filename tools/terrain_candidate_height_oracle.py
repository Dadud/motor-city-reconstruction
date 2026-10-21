"""Compare a supplied-world terrain candidate height rejection with original 0x45a320."""
import argparse
import json
import struct

from unicorn import UC_HOOK_CODE

from client.collision_terrain import sample_triangle_candidate_heights
from tools.native_oracle import DynoOracle
from tools.support_correction_oracle import _install_world, _make_world
from tools.track_surface_cases import fixture


OWNER = 0x71008000
TABLE = 0x88C9D4


def compare(executable):
    arena, root, seed = fixture(2, 0, 0, 0, 7, 8, 8, 1)
    world = _make_world(arena, root)
    vertices = ((6., 1., 6.), (6., 1., 10.), (10., 1., 6.))
    object_normal = (0., 1., 0.)
    object_plane_point = (0., 0., 0.)
    sampled = sample_triangle_candidate_heights(
        world, vertices, seed, object_normal, object_plane_point)
    expected = sampled.candidate
    if expected.accepted or expected.minimum_gap <= 0.1016:
        raise AssertionError(f'height fixture should reject, got {expected!r}')

    oracle = DynoOracle(executable)
    cpu = oracle.cpu
    _install_world(oracle, arena, root)
    cpu.mem_write(TABLE, struct.pack('<36I', *([0, 1, 2] * 12)))
    image = bytearray(0xA00)
    struct.pack_into('<f', image, 8, 8.)
    struct.pack_into('<f', image, 0x10, 8.)
    struct.pack_into('<I', image, 0xdc, 0)
    struct.pack_into('<3f', image, 0x328, *object_normal)
    struct.pack_into('<3f', image, 0x340, *object_plane_point)
    struct.pack_into('<9f', image, 0x1e8, *(v for vertex in vertices for v in vertex))
    image[0x370:0x370 + 0x44] = seed[:0x44]
    cpu.mem_write(OWNER, bytes(image))
    counts = {0x42E760: 0, 0x42DC50: 0, 0x457550: 0}
    cpu.hook_add(UC_HOOK_CODE,
                 lambda _cpu, address, _size, _user:
                 counts.__setitem__(address, counts[address] + 1)
                 if address in counts else None)
    before = bytes(cpu.mem_read(OWNER, len(image)))
    oracle.call(0x45A320, (OWNER,), instruction_limit=1_000_000)
    actual = cpu.reg_read(oracle.reg.UC_X86_REG_EAX)
    if actual != 0:
        raise AssertionError(f'original candidate returned {actual}, expected rejection')
    if counts != {0x42E760: 3, 0x42DC50: 3, 0x457550: 0}:
        raise AssertionError(f'original followed unexpected candidate path: {counts!r}')
    if bytes(cpu.mem_read(OWNER, len(image))) != before:
        raise AssertionError('original changed the object on height-gate rejection')
    return {'entry': '0x45a320', 'terrain_vertex_queries': counts[0x42E760],
            'triangle_plane_queries': counts[0x42DC50],
            'minimum_signed_height_gap': expected.minimum_gap,
            'original_response_calls': counts[0x457550],
            'scope': 'one supplied flat-world triangle rejected by 0.1016 height gate'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    print(json.dumps(compare(parser.parse_args().executable)))
