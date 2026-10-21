"""Compare the owner-write portion of 0x53d7b0 to the original."""
import argparse
import random
import struct
from pathlib import Path

from client.world_object_reset import OWNER_SIZE, reset_world_object_track_rate
from tools.native_oracle import DynoOracle


OWNER = 0x72002000
PROFILE = 0x71005000
CHILD = 0x0053D640


def verify(executable, cases=256):
    oracle = DynoOracle(executable)
    cpu, reg = oracle.cpu, oracle.reg
    rng = random.Random(0x53D7B0)
    # 0x53d7b0 begins by invoking the separate geometry/drive reset helper.
    # Replace only that child with RET; then compare every owner byte written
    # by 0x53d7b0 itself.
    cpu.mem_write(CHILD, b'\xc3')
    if hasattr(cpu, 'ctl_flush_tb'):
        cpu.ctl_flush_tb()
    for case in range(cases):
        initial = bytearray(rng.randbytes(OWNER_SIZE))
        profile = bytearray(rng.randbytes(0x78))
        rate = rng.uniform(-100.0, 100.0)
        struct.pack_into('<I', initial, 0x1c94, PROFILE)
        struct.pack_into('<f', initial, 0x1818, rng.uniform(-10.0, 10.0))
        for offset in (0x1810, 0x1814, 0x1818, 0x181c):
            struct.pack_into('<f', initial, offset, rng.uniform(-10, 10))
        struct.pack_into('<3f', initial, 0xa3c, *(rng.uniform(-10, 10) for _ in range(3)))
        for offset in (0x78, 0x7c, 0x80, 0x84, 0x88, 0x8c,
                       0x90, 0x94, 0x98):
            struct.pack_into('<f', initial, offset, rng.uniform(-10, 10))
        for wheel in range(4):
            struct.pack_into('<f', initial, 0x668 + wheel * 0x10c + 0x50,
                             rng.choice((-1.0, -0.25, 0.25, 1.0, 3.0, 10.0)))
        struct.pack_into('<i', profile, 0x70, rng.randint(-50, 50))
        cpu.mem_write(OWNER, bytes(initial))
        cpu.mem_write(PROFILE, bytes(profile))
        oracle.call(0x0053D7B0, (OWNER, struct.unpack('<I', struct.pack('<f', rate))[0]),
                    instruction_limit=100000)
        original = bytes(cpu.mem_read(OWNER, OWNER_SIZE))
        translated = bytearray(initial)
        reset_world_object_track_rate(translated, rate, profile)
        if original != translated:
            differences = [i for i, (left, right) in enumerate(zip(original, translated))
                           if left != right]
            raise AssertionError(f'0x53d7b0 owner mismatch case {case}; '
                                 f'bytes {[hex(i) for i in differences[:24]]}; '
                                 f'native={[(hex(i), original[i:i+4].hex()) for i in differences[:8]]}; '
                                 f'python={[(hex(i), translated[i:i+4].hex()) for i in differences[:8]]}')
    return cases


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', type=Path)
    parser.add_argument('--cases', type=int, default=256)
    args = parser.parse_args()
    count = verify(args.executable, args.cases)
    print(f'0x53d7b0 owner writes match {count} original cases with 0x53d640 intercepted')


if __name__ == '__main__':
    main()
