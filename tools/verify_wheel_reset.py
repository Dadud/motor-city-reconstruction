"""Compare 0x53d4a0's four wheel-record resets with the original binary."""
import argparse
import random
import struct
from pathlib import Path

from client.tire_response import f32
from client.world_object_reset import (OWNER_SIZE, WheelResetCache,
                                       reset_wheel_records)
from tools.native_oracle import DynoOracle

OWNER = 0x72002000
PROFILE = 0x71005000
INIT_FLAG = 0x00A55700
FACTOR = 0x00A55704


def verify(executable, cases=96):
    oracle = DynoOracle(executable)
    cpu = oracle.cpu
    rng = random.Random(0x53D4A0)
    for case in range(cases):
        initial = bytearray(rng.randbytes(OWNER_SIZE))
        profile_scale = f32(rng.uniform(0.1, 20.0))
        initialized = bool(case & 1)
        initial_factor = f32(rng.uniform(0.1, 5.0))
        struct.pack_into('<I', initial, 0x1c94, PROFILE)
        cpu.mem_write(PROFILE + 0x20, struct.pack('<f', profile_scale))
        cpu.mem_write(OWNER, bytes(initial))
        cpu.mem_write(INIT_FLAG, struct.pack('<I', int(initialized)))
        cpu.mem_write(FACTOR, struct.pack('<f', initial_factor))
        oracle.call(0x0053D4A0, (OWNER,), instruction_limit=200000)
        original = bytes(cpu.mem_read(OWNER, OWNER_SIZE))
        original_globals = bytes(cpu.mem_read(INIT_FLAG, 8))

        translated = bytearray(initial)
        cache = WheelResetCache(initialized, initial_factor)
        reset_wheel_records(translated, cache=cache, profile_scale=profile_scale)
        expected_globals = struct.pack('<If', int(cache.initialized), f32(cache.factor))
        if original != translated:
            differences = [i for i, (left, right) in enumerate(zip(original, translated))
                           if left != right]
            raise AssertionError(f'0x53d4a0 owner mismatch case {case}; '
                                 f'bytes {[hex(i) for i in differences[:20]]}; '
                                 f'original={[(hex(i), original[i:i+4].hex()) for i in differences[:8]]}; '
                                 f'python={[(hex(i), translated[i:i+4].hex()) for i in differences[:8]]}')
        if original_globals != expected_globals:
            raise AssertionError(f'0x53d4a0 lazy-global mismatch case {case}: '
                                 f'{original_globals.hex()} != {expected_globals.hex()}')
    return cases


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', type=Path)
    parser.add_argument('--cases', type=int, default=96)
    args = parser.parse_args()
    count = verify(args.executable, args.cases)
    print(f'0x53d4a0 matches {count} original wheel-record sets and lazy-cache states')


if __name__ == '__main__':
    main()
