"""Compare surface descriptor-to-vertex resolution with native 0x42e3f0."""
import argparse
import json
import random
import struct

from client.track_surface import surface_quad_vertex_indices
from tools.native_oracle import DynoOracle


PARAM, BLOCKS = 0x71000100, 0x71001000
QUADS, DESCRIPTORS, VERTICES = 0x71004000, 0x71006000, 0x71007000


def verify(executable, cases=512):
    if type(cases) is not int or not 1 <= cases <= 10_000:
        raise ValueError('cases must be between 1 and 10000')
    oracle = DynoOracle(executable)
    rng = random.Random(0x42E3F0)
    for case in range(cases):
        block_count = 1 + case % 5
        block = rng.randrange(block_count)
        descriptor_count = 1 + case % 12
        descriptor = rng.randrange(descriptor_count)
        quad_count = 1 + case % 7
        quads = tuple(tuple(rng.randrange(256) for _ in range(4))
                      for _ in range(quad_count))
        descriptors = tuple((0, 0, 0, rng.randrange(quad_count))
                            for _ in range(descriptor_count))
        expected = surface_quad_vertex_indices(block, descriptor, descriptors, quads)

        native_blocks = bytearray(block_count * 0x6c4)
        native_quads = bytearray(block_count * 0x200)
        native_descriptors = bytearray(block_count * 0x200)
        vertex_ptr = VERTICES + block * 0x1000
        quad_ptr = QUADS + block * 0x200
        descriptor_ptr = DESCRIPTORS + block * 0x200
        base = block * 0x6c4
        struct.pack_into('<I', native_blocks, base + 0x14c, vertex_ptr)
        struct.pack_into('<I', native_blocks, base + 0x3c, quad_ptr)
        struct.pack_into('<I', native_blocks, base + 0x67c, descriptor_ptr)
        for index, indices in enumerate(quads):
            struct.pack_into('<4H', native_quads,
                             block * 0x200 + index * 0x1e, *indices)
        for index, record in enumerate(descriptors):
            struct.pack_into('<H', native_descriptors,
                             block * 0x200 + index * 0x14 + 6, record[3])

        outputs = tuple(PARAM + 0x20 + index * 4 for index in range(4))
        oracle._reset()
        oracle.cpu.mem_write(PARAM, struct.pack('<HH', block, descriptor))
        oracle.cpu.mem_write(PARAM + 4, bytes(0x20))
        oracle.cpu.mem_write(BLOCKS, bytes(native_blocks))
        oracle.cpu.mem_write(QUADS, bytes(native_quads))
        oracle.cpu.mem_write(DESCRIPTORS, bytes(native_descriptors))
        oracle.cpu.mem_write(0x0097c408, struct.pack('<I', BLOCKS))
        oracle.call(0x42E3F0, (PARAM, *outputs), instruction_limit=100_000)
        actual = tuple(struct.unpack('<I', oracle.cpu.mem_read(address, 4))[0]
                       for address in outputs)
        expected_ptrs = tuple(vertex_ptr + index * 12 for index in expected)
        if actual != expected_ptrs:
            raise AssertionError(
                f'case {case}: native pointers={actual!r}, '
                f'expected={expected_ptrs!r}, block={block}, descriptor={descriptor}')
    return {'entry': '0x42e3f0', 'cases': cases,
            'scope': 'surface descriptor to four vertex pointers over explicit block tables'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    parser.add_argument('--cases', type=int, default=512)
    args = parser.parse_args()
    print(json.dumps(verify(args.executable, args.cases)))


if __name__ == '__main__':
    main()
