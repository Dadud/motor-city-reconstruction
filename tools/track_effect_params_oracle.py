"""Compare the native 0x494dc0 parameter normalizer byte-for-byte."""
import argparse
import json
import math
import random
import struct

from client.track_effect_params import BLOCK_SIZE, prepare_track_effect_params
from tools.native_oracle import DynoOracle


def _float_choice(rng, index):
    choices = (0.0, -0.0, 1.0, -1.0, math.nan, math.inf, -math.inf)
    return choices[index % len(choices)] if index % 3 == 0 else rng.uniform(-1000, 1000)


def compare(executable, cases=256):
    if type(cases) is not int or not 1 <= cases <= 10000:
        raise ValueError('case count must be between 1 and 10000')
    oracle = DynoOracle(executable)
    rng = random.Random(0x494dc0)
    for index in range(cases):
        native_input = bytearray(rng.randbytes(BLOCK_SIZE))
        struct.pack_into('<i', native_input, 0xC0D8,
                         rng.choice((0, 1, -1, 3, 100, rng.randint(-1000, 1000))))
        struct.pack_into('<i', native_input, 0xC0C8, rng.randint(-1000, 1000))
        struct.pack_into('<i', native_input, 0xC0D0, rng.randint(-1000, 1000))
        struct.pack_into('<f', native_input, 0xC118, _float_choice(rng, index))
        struct.pack_into('<f', native_input, 0xC11C, _float_choice(rng, index+2))
        struct.pack_into('<i', native_input, 0xC134,
                         rng.choice((-360000, -360, -90, 0, 90, 360, 360000,
                                     rng.randint(-1_000_000, 1_000_000))))
        struct.pack_into('<i', native_input, 0xC130,
                         rng.choice((-1_000_000, -5000, -1, 0, 1, 5000, 1_000_000)))
        translated = bytearray(native_input)
        prepare_track_effect_params(translated)
        oracle.cpu.mem_write(oracle.inputs, bytes(native_input))
        oracle.call(0x494dc0, (oracle.inputs,), instruction_limit=100_000)
        actual = bytes(oracle.cpu.mem_read(oracle.inputs, BLOCK_SIZE))
        expected = bytes(translated)
        if actual != expected:
            offset = next(i for i, (a, b) in enumerate(zip(actual, expected)) if a != b)
            raise AssertionError(
                f'case {index}, first mismatch at +{offset:#x}: '
                f'native={actual[offset:offset+4].hex()} '
                f'python={expected[offset:offset+4].hex()}')
    return {
        'entry': '0x494dc0',
        'cases': cases,
        'block_bytes_per_case': BLOCK_SIZE,
        'all_bytes_matched': True,
        'scope': 'original helper emulated on supplied parameter blocks; '
                 'the parent renderer and live graphics APIs are excluded',
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    parser.add_argument('--cases', type=int, default=256)
    args = parser.parse_args()
    print(json.dumps(compare(args.executable, args.cases)))
