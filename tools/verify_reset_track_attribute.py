"""Compare the table-backed reset byte lookup 0x403000 to the original."""
import argparse
import random
import struct
from pathlib import Path

from client.track_topology import reset_track_attribute
from tools.native_oracle import DynoOracle


TABLE = 0x71000000
OUTPUT = 0x72000000
TRACK_TABLE = 0x008E3AB8
DEFAULT_FLOAT = 0x0083B638


def verify(executable, cases=256):
    oracle = DynoOracle(executable)
    cpu = oracle.cpu
    rng = random.Random(0x403000)
    for case in range(cases):
        rows = rng.randrange(1, 512)
        table = bytearray(rng.randbytes(rows * 0x1c))
        row = rng.randrange(rows)
        selector = rng.randrange(2)
        default = rng.randrange(256)
        cpu.mem_write(TRACK_TABLE, struct.pack('<I', TABLE))
        cpu.mem_write(TABLE, bytes(table))
        cpu.mem_write(DEFAULT_FLOAT, struct.pack('<f', float(default)))
        # Store ST0 before returning; compare the helper's return without
        # trusting Unicorn to preserve the caller's x87 result stack.
        oracle.call(0x00403000, (row, 0, selector),
                    tail=b'\xd9\x1d' + struct.pack('<I', OUTPUT))
        original = struct.unpack('<f', cpu.mem_read(OUTPUT, 4))[0]
        translated = reset_track_attribute(table, row, selector,
                                           default_value=default)
        if original != float(translated):
            raise AssertionError(f'0x403000 mismatch in case {case}: '
                                 f'row={row}, selector={selector}, '
                                 f'original={original}, translated={translated}')

    # The original null-table path returns the supplied global default.
    cpu.mem_write(TRACK_TABLE, struct.pack('<I', 0))
    cpu.mem_write(DEFAULT_FLOAT, struct.pack('<f', 37.0))
    oracle.call(0x00403000, (0x7fffffff, 0, 0),
                tail=b'\xd9\x1d' + struct.pack('<I', OUTPUT))
    original = struct.unpack('<f', cpu.mem_read(OUTPUT, 4))[0]
    translated = reset_track_attribute(None, 0, 0, default_value=37)
    if original != float(translated):
        raise AssertionError('0x403000 null-table fallback mismatch')
    return cases + 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', type=Path)
    parser.add_argument('--cases', type=int, default=256)
    args = parser.parse_args()
    count = verify(args.executable, args.cases)
    print(f'0x403000 table and null-table behavior match {count} original calls')


if __name__ == '__main__':
    main()
