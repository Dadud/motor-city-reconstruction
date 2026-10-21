"""Compare the complete mapped path-index helper 0x405930 to the original."""
import argparse
import random
import struct
from pathlib import Path

from client.track_topology import reset_path_index
from tools.native_oracle import DynoOracle


GLOBALS = (0x009AAA98, 0x00988E38, 0x009AAA78, 0x009AAA7C,
           0x009AAA74, 0x009AAA54)


def verify(executable, cases=10000):
    oracle = DynoOracle(executable)
    cpu = oracle.cpu
    rng = random.Random(0x405930)
    for case in range(cases):
        count = rng.randrange(1, 200)
        fallback = rng.randrange(0, 200)
        origin = rng.randrange(0, 200)
        secondary = rng.randrange(0, 200)
        wrapped = rng.randrange(2)
        reverse = rng.randrange(2)
        index = rng.randrange(0, 400)
        offset = rng.randint(-100, 100)
        values = (count, fallback, origin, secondary, wrapped, reverse)
        for address, value in zip(GLOBALS, values):
            cpu.mem_write(address, struct.pack('<I', value))
        oracle.call(0x00405930, (index, offset))
        original = cpu.reg_read(oracle.reg.UC_X86_REG_EAX)
        translated = reset_path_index(
            index, offset, primary_count=count, fallback_count=fallback,
            primary_origin=origin, secondary_origin=secondary,
            wrapped_mode=wrapped, reverse_mode=reverse)
        if original != (translated & 0xffffffff):
            raise AssertionError(f'0x405930 mismatch in case {case}: '
                                 f'{values + (index, offset)}, '
                                 f'original={original:#x}, translated={translated & 0xffffffff:#x}')
    return cases


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', type=Path)
    parser.add_argument('--cases', type=int, default=10000)
    args = parser.parse_args()
    count = verify(args.executable, args.cases)
    print(f'0x405930 path mapping matches {count} original calls across all branches')


if __name__ == '__main__':
    main()
