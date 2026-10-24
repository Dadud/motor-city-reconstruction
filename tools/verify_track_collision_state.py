"""Compare track collision-state reset with native routine 0x42d2e0."""
import argparse
import json
import random
import struct

from client.track_collision_state import (reset_secondary_collision_table,
    reset_track_collision_state)
from tools.native_oracle import DynoOracle


METADATA, BLOCKS, SECONDARY = 0x0097DBF0, 0x71001000, 0x008E3B38
ARRAYS = 0x71004000


def verify(executable, cases=256):
    if type(cases) is not int or not 1 <= cases <= 10_000:
        raise ValueError('cases must be between 1 and 10000')
    oracle = DynoOracle(executable)
    rng = random.Random(0x42D2E0)
    for case in range(cases):
        bound = -1 if case % 9 == 0 else case % 6
        row_count = max(bound + 1, 1)
        block_table = bytearray(rng.getrandbits(8) for _ in range(row_count * 0x6C4))
        pointed = {}
        for row in range(row_count):
            entry_count = (-1, 0, 1, 2, 5)[(case + row) % 5]
            pointer = 0 if (case + row) % 4 == 0 else ARRAYS + row * 0x100
            struct.pack_into('<iI', block_table, row * 0x6C4 + 0x69C,
                             entry_count, pointer)
            if pointer:
                length = 2 + max(entry_count, 1) * 24
                pointed[pointer] = bytearray(rng.getrandbits(8) for _ in range(length))
        metadata = bytearray(rng.getrandbits(8) for _ in range(0xC00))
        secondary = bytearray(rng.getrandbits(8) for _ in range(0x1800))
        expected_metadata = bytearray(metadata)
        expected_blocks = bytearray(block_table)
        expected_pointed = {address: bytearray(image)
                            for address, image in pointed.items()}
        expected_secondary = bytearray(secondary)
        reset_track_collision_state(expected_metadata, expected_blocks, bound,
                                    expected_pointed, expected_secondary)

        direct_secondary = bytearray(secondary)
        reset_secondary_collision_table(direct_secondary)
        oracle._reset()
        oracle.cpu.mem_write(SECONDARY, bytes(secondary))
        oracle.call(0x407550, (), instruction_limit=100_000)
        actual_secondary = bytes(oracle.cpu.mem_read(SECONDARY, len(secondary)))
        if actual_secondary != direct_secondary:
            offset = next(i for i, (a, b) in enumerate(
                zip(actual_secondary, direct_secondary)) if a != b)
            raise AssertionError(
                f'case {case}, 0x407550 byte {offset:#x} differs')

        oracle._reset()
        oracle.cpu.mem_write(METADATA, bytes(metadata))
        oracle.cpu.mem_write(BLOCKS, bytes(block_table))
        oracle.cpu.mem_write(SECONDARY, bytes(secondary))
        for address, image in pointed.items():
            oracle.cpu.mem_write(address, bytes(image))
        oracle.cpu.mem_write(0x0097C408, struct.pack('<I', BLOCKS))
        oracle.cpu.mem_write(0x0097DBEC, struct.pack('<i', bound))
        oracle.call(0x42D2E0, (), instruction_limit=1_000_000)

        comparisons = [(METADATA, expected_metadata),
                       (BLOCKS, expected_blocks),
                       (SECONDARY, expected_secondary)]
        comparisons.extend((address, image) for address, image in expected_pointed.items())
        for address, expected in comparisons:
            actual = bytes(oracle.cpu.mem_read(address, len(expected)))
            if actual != expected:
                offset = next(i for i, (a, b) in enumerate(zip(actual, expected)) if a != b)
                raise AssertionError(
                    f'case {case}, memory {address:#x}+{offset:#x}: '
                    f'native={actual[offset]:#04x} port={expected[offset]:#04x}')
    return {'entry': '0x42d2e0', 'cases': cases,
            'direct_0x407550_cases': cases,
            'scope': 'complete parent memory images and direct secondary-reset table images'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    parser.add_argument('--cases', type=int, default=256)
    args = parser.parse_args()
    print(json.dumps(verify(args.executable, args.cases)))


if __name__ == '__main__':
    main()
