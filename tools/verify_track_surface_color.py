"""Compare packed surface color averaging with native 0x42e490."""
import argparse
import json
import random
import struct

from client.track_surface import average_surface_vertex_color
from tools.native_oracle import DynoOracle


PARAM, DESCRIPTOR, COLORS, QUADS = 0x71000100, 0x71000200, 0x71001000, 0x71002000
BLOCKS = 0x71003000


def verify(executable, cases=512):
    if type(cases) is not int or not 1 <= cases <= 10_000:
        raise ValueError('cases must be between 1 and 10000')
    oracle = DynoOracle(executable)
    rng = random.Random(0x42E490)
    for case in range(cases):
        block = case % 5
        quad = case % 3
        colors = tuple(rng.getrandbits(32) for _ in range(16))
        quads = tuple(tuple(rng.randrange(16) for _ in range(4)) for _ in range(3))
        descriptor = (0, 0, 0, quad)
        expected = average_surface_vertex_color(block, descriptor, colors, quads)

        # Native block table uses +0x150 for the color array and +0x3c for quads.
        native_blocks = bytearray((block + 1) * 0x6c4)
        block_offset = block * 0x6c4
        struct.pack_into('<I', native_blocks, block_offset + 0x150, COLORS)
        struct.pack_into('<I', native_blocks, block_offset + 0x3c, QUADS)
        native_colors = b''.join(struct.pack('<I', value) for value in colors)
        native_quads = bytearray(3 * 0x1e)
        for index, indices in enumerate(quads):
            struct.pack_into('<4H', native_quads, index * 0x1e, *indices)

        oracle._reset()
        oracle.cpu.mem_write(PARAM, bytes(0x10))
        oracle.cpu.mem_write(PARAM + 4, struct.pack('<I', block))
        oracle.cpu.mem_write(PARAM + 0xc, struct.pack('<I', DESCRIPTOR))
        oracle.cpu.mem_write(DESCRIPTOR + 6, struct.pack('<H', quad))
        oracle.cpu.mem_write(COLORS, native_colors)
        oracle.cpu.mem_write(QUADS, bytes(native_quads))
        oracle.cpu.mem_write(BLOCKS, bytes(native_blocks))
        oracle.cpu.mem_write(0x0097c408, struct.pack('<I', BLOCKS))
        oracle.call(0x42E490, (PARAM,), instruction_limit=100_000)
        actual = oracle.cpu.reg_read(oracle.reg.UC_X86_REG_EAX)
        if actual != expected:
            raise AssertionError(
                f'case {case}: native color={actual:#010x}, '
                f'expected={expected:#010x}, block={block}, quad={quad}')

        # The null descriptor bypasses all world pointers and returns fixed gray.
        oracle._reset()
        oracle.cpu.mem_write(PARAM + 0xc, bytes(4))
        oracle.call(0x42E490, (PARAM,), instruction_limit=100_000)
        actual = oracle.cpu.reg_read(oracle.reg.UC_X86_REG_EAX)
        if actual != 0xff7f7f7f:
            raise AssertionError(f'null case {case}: got {actual:#010x}')
    return {'entry': '0x42e490', 'cases': cases,
            'scope': 'four vertex packed-color averaging and null descriptor fallback'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    parser.add_argument('--cases', type=int, default=512)
    args = parser.parse_args()
    print(json.dumps(verify(args.executable, args.cases)))


if __name__ == '__main__':
    main()
