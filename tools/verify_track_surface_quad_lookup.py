"""Compare native 0x42eed0 quad traversal with its supplied candidate leaf."""
import argparse
import json
import random
import struct

from client.track_surface import find_surface_quad_candidate
from tools.native_oracle import DynoOracle


LEAF, CANDIDATES, POINT, BLOCKS = 0x71000100, 0x71000200, 0x71000300, 0x71001000
QUADS, DESCRIPTORS, VERTICES = 0x71004000, 0x71006000, 0x71007000
LEAF_SENTINEL = 0xDEADBEEF
GRID_STUB = 0x70001000


def _install_grid_leaf(oracle, leaf):
    oracle.cpu.mem_write(GRID_STUB, b'\xB8' + struct.pack('<I', leaf) + b'\xC3')
    displacement = GRID_STUB - (0x42EEDD + 5)
    oracle.cpu.mem_write(0x42EEDD, b'\xE8' + struct.pack('<i', displacement))


def verify(executable, cases=512):
    if type(cases) is not int or not 1 <= cases <= 10_000:
        raise ValueError('cases must be between 1 and 10000')
    oracle = DynoOracle(executable)
    rng = random.Random(0x42EED0)
    for case in range(cases):
        block_count = 1 + case % 4
        blocks, encoded_candidates = [], []
        native_blocks = bytearray(block_count * 0x6C4)
        native_quads = bytearray(block_count * 0x400)
        native_descriptors = bytearray(block_count * 0x200)
        native_vertices = bytearray(block_count * 0x200)
        for block in range(block_count):
            block_quads = ((0, 1, 2, 3), (4, 5, 6, 7))
            block_vertices = []
            for polygon in range(2):
                left = block * 50.0 + polygon * 20.0
                block_vertices.extend(((left, 0., 0.), (left + 10., 0., 0.),
                                       (left + 10., 1., 10.), (left, 1., 10.)))
            descriptor_count = 4
            block_descriptors = tuple((0, 0, 0, item % 2)
                                      for item in range(descriptor_count))
            blocks.append((tuple(block_vertices), block_quads, block_descriptors))
            header = block * 0x6C4
            quad_ptr = QUADS + block * 0x400
            descriptor_ptr = DESCRIPTORS + block * 0x200
            vertex_ptr = VERTICES + block * 0x200
            struct.pack_into('<I', native_blocks, header + 0x3C, quad_ptr)
            struct.pack_into('<I', native_blocks, header + 0x14C, vertex_ptr)
            struct.pack_into('<I', native_blocks, header + 0x67C, descriptor_ptr)
            for polygon, indices in enumerate(block_quads):
                struct.pack_into('<4H', native_quads,
                                 block * 0x400 + polygon * 0x1E, *indices)
            for descriptor, value in enumerate(block_descriptors):
                struct.pack_into('<H', native_descriptors,
                                 block * 0x200 + descriptor * 0x14 + 6,
                                 value[3])
            for vertex, xyz in enumerate(block_vertices):
                struct.pack_into('<3f', native_vertices,
                                 block * 0x200 + vertex * 12, *xyz)
        candidate_count = case % 8
        for _ in range(candidate_count):
            encoded_candidates.append((rng.randrange(block_count), rng.randrange(4)))
        if candidate_count and case % 3 != 0:
            chosen_block, chosen_descriptor = encoded_candidates[-1]
            polygon = chosen_descriptor % 2
            x = chosen_block * 50. + polygon * 20. + (0.0, 5.0, 10.0)[case % 3]
            z = (0.0, 5.0, 10.0)[(case // 3) % 3]
        else:
            x, z = 500., 500.
        point = (x, rng.uniform(-5., 5.), z)
        expected_candidate = find_surface_quad_candidate(
            point[0], point[2], encoded_candidates, blocks)
        expected_index = (encoded_candidates.index(expected_candidate)
                          if expected_candidate is not None else None)
        sentinel = 0 if case % 13 == 1 else LEAF_SENTINEL
        leaf_ptr = 0 if case % 13 == 0 else LEAF
        exposed_count = 0 if case % 13 == 2 else candidate_count
        expected_pointer = (CANDIDATES + expected_index * 4
                            if leaf_ptr and sentinel == LEAF_SENTINEL
                            and exposed_count > 0 and expected_index is not None
                            else 0)

        oracle._reset()
        _install_grid_leaf(oracle, leaf_ptr)
        oracle.cpu.mem_write(LEAF, struct.pack('<III', sentinel,
            exposed_count, CANDIDATES))
        if encoded_candidates:
            oracle.cpu.mem_write(CANDIDATES, b''.join(
                struct.pack('<HH', *item) for item in encoded_candidates))
        oracle.cpu.mem_write(POINT, struct.pack('<3f', *point))
        oracle.cpu.mem_write(BLOCKS, bytes(native_blocks))
        oracle.cpu.mem_write(QUADS, bytes(native_quads))
        oracle.cpu.mem_write(DESCRIPTORS, bytes(native_descriptors))
        oracle.cpu.mem_write(VERTICES, bytes(native_vertices))
        oracle.cpu.mem_write(0x0097C408, struct.pack('<I', BLOCKS))
        oracle.call(0x42EED0, (POINT,), instruction_limit=1_000_000)
        actual_pointer = oracle.cpu.reg_read(oracle.reg.UC_X86_REG_EAX)
        if actual_pointer != expected_pointer:
            raise AssertionError(
                f'case {case}: native pointer={actual_pointer:#x}, '
                f'expected={expected_pointer:#x}, candidates={encoded_candidates}, '
                f'point={point}')
    return {'entry': '0x42eed0', 'cases': cases,
            'scope': 'ordered quad-candidate traversal and return pointer with spatial leaf supplied at the child boundary'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    parser.add_argument('--cases', type=int, default=512)
    args = parser.parse_args()
    print(json.dumps(verify(args.executable, args.cases)))


if __name__ == '__main__':
    main()
