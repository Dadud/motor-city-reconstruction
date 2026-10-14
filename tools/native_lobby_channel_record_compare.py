"""Compare native channel-image writes to the original-verified Python model.

Private synthetic layout fixtures only; no credentials, original host pointers,
socket operations or live channel choices.
"""
import argparse
import json
from pathlib import Path
import random
import struct
import subprocess

from client.lobby_channel_record import (CHANNEL_ARGUMENT_SIZE, CHANNEL_ALLOCATION_SIZE,
                                        initialize_channel_image, materialize_channel_record)


def verify(runner):
    runner = str(Path(runner).resolve())
    rng = random.Random(0x743d50)
    constructor_count = record_count = rejected = 0

    def compare(mode, data, expected):
        result = subprocess.run([runner, mode], input=data, capture_output=True, timeout=10)
        if result.returncode or result.stdout != expected:
            raise AssertionError(f'native {mode} differs from original-verified Python model')

    # Every combination of the four inspected flag bits, with unrelated flag
    # bits randomized as well. Name copy boundaries include NUL after 30 bytes.
    bits = (1, 4, 0x20, 0x4000)
    for mask in range(16):
        flag_bits = sum(bit for index, bit in enumerate(bits) if mask & (1 << index))
        for extra in (0, rng.getrandbits(32) & ~sum(bits)):
            flags = flag_bits | extra
            for name_size in (0, 1, 29, 30, 31, 32):
                argument = bytearray(rng.randbytes(CHANNEL_ARGUMENT_SIZE))
                struct.pack_into('<I', argument, 0xc, flags)
                argument[0x10:0x30] = b'n' * name_size + bytes(32 - name_size)
                allocated = rng.randbytes(CHANNEL_ALLOCATION_SIZE)
                image = initialize_channel_image(bytes(argument), allocated)
                compare('initialize', bytes(argument) + allocated, image)
                constructor_count += 1
                supplied = bytearray(image)
                for offset in (8, 0x2c, 0x30, 0x34, 0x58, 0x5c, 0x60):
                    struct.pack_into('<I', supplied, offset, rng.getrandbits(32))
                record = materialize_channel_record(bytes(supplied)).native
                compare('materialize', bytes(supplied), record)
                record_count += 1
    # Unconstrained source data checks byte preservation independent of constructor.
    for _ in range(32):
        supplied = rng.randbytes(CHANNEL_ALLOCATION_SIZE)
        compare('materialize', supplied, materialize_channel_record(supplied).native)
        record_count += 1
    for mode, size in (('initialize', CHANNEL_ARGUMENT_SIZE + CHANNEL_ALLOCATION_SIZE),
                       ('materialize', CHANNEL_ALLOCATION_SIZE)):
        for length in (0, size - 1, size + 1):
            result = subprocess.run([runner, mode], input=bytes(length), capture_output=True, timeout=10)
            if result.returncode != 2 or result.stdout:
                raise AssertionError('native runner accepted invalid input size')
            rejected += 1
    return {'matched_constructor_cases': constructor_count, 'matched_record_cases': record_count,
            'invalid_runner_inputs_rejected': rejected, 'original_binary_executed': False,
            'live_server_tested': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('runner')
    print(json.dumps(verify(parser.parse_args().runner), indent=2))
