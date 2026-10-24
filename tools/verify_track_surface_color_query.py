"""Compare the 0x42e590 candidate-to-color path with the original client."""
import argparse
import json
import random
import struct

from client.track_surface import surface_color_from_candidate
from tools.native_oracle import DynoOracle


PARAM, CANDIDATE, COLORS, QUADS, DESCRIPTORS = (
    0x71000100, 0x71000200, 0x71001000, 0x71002000, 0x71003000)
BLOCKS, STUB = 0x71004000, 0x70001000


def _install_candidate_stub(oracle, candidate):
    oracle.cpu.mem_write(STUB, b'\xb8' + struct.pack('<I', candidate) + b'\xc3')
    displacement = STUB - (0x42E597 + 5)
    oracle.cpu.mem_write(0x42E597, b'\xe8' + struct.pack('<i', displacement))


def verify(executable, cases=512):
    if type(cases) is not int or not 1 <= cases <= 10_000:
        raise ValueError('cases must be between 1 and 10000')
    oracle = DynoOracle(executable)
    rng = random.Random(0x42E590)
    for case in range(cases):
        block_count = 1 + case % 5
        block = rng.randrange(block_count)
        quad_count = 1 + case % 8
        descriptor_count = 1 + case % 11
        colors = tuple(rng.getrandbits(32) for _ in range(32))
        quads = tuple(tuple(rng.randrange(len(colors)) for _ in range(4))
                      for _ in range(quad_count))
        descriptors = tuple((0, 0, 0, rng.randrange(quad_count))
                            for _ in range(descriptor_count))
        candidate_index = case % descriptor_count
        candidate = (block, candidate_index)
        blocks = tuple(((), quads, descriptors, colors) for _ in range(block_count))
        expected = surface_color_from_candidate(candidate, blocks)

        block_bytes = bytearray(block_count * 0x6c4)
        base = block * 0x6c4
        struct.pack_into('<I', block_bytes, base + 0x3c, QUADS)
        struct.pack_into('<I', block_bytes, base + 0x67c, DESCRIPTORS)
        struct.pack_into('<I', block_bytes, base + 0x150, COLORS)
        quad_bytes = bytearray(quad_count * 0x1e)
        for index, indices in enumerate(quads):
            struct.pack_into('<4H', quad_bytes, index * 0x1e, *indices)
        descriptor_bytes = bytearray(descriptor_count * 0x14)
        for index, record in enumerate(descriptors):
            struct.pack_into('<H', descriptor_bytes, index * 0x14 + 6, record[3])

        oracle._reset()
        _install_candidate_stub(oracle, CANDIDATE)
        oracle.cpu.mem_write(PARAM, struct.pack('<HH', *candidate))
        oracle.cpu.mem_write(CANDIDATE, struct.pack('<HH', *candidate))
        oracle.cpu.mem_write(COLORS, b''.join(struct.pack('<I', color) for color in colors))
        oracle.cpu.mem_write(QUADS, bytes(quad_bytes))
        oracle.cpu.mem_write(DESCRIPTORS, bytes(descriptor_bytes))
        oracle.cpu.mem_write(BLOCKS, bytes(block_bytes))
        oracle.cpu.mem_write(0x0097C408, struct.pack('<I', BLOCKS))
        oracle.call(0x42E590, (PARAM,), instruction_limit=100_000)
        actual = oracle.cpu.reg_read(oracle.reg.UC_X86_REG_EAX)
        if actual != expected:
            raise AssertionError(
                f'case {case}: native color={actual:#010x}, expected={expected:#010x}, '
                f'candidate={candidate}')

        oracle._reset()
        _install_candidate_stub(oracle, 0)
        oracle.call(0x42E590, (PARAM,), instruction_limit=100_000)
        actual = oracle.cpu.reg_read(oracle.reg.UC_X86_REG_EAX)
        if actual != 0xffffffff:
            raise AssertionError(f'no-hit case {case}: native result={actual:#010x}')
    return {'entry': '0x42e590', 'cases': cases,
            'scope': 'surface candidate lookup boundary followed by native packed-color average'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    parser.add_argument('--cases', type=int, default=512)
    args = parser.parse_args()
    print(json.dumps(verify(args.executable, args.cases)))


if __name__ == '__main__':
    main()
