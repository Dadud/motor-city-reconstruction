"""Compare the 0x6f1530/1590/15f0 axis matrices with mcity.exe."""
import argparse
import json
import random
import struct

from client.matrix_math import rotation_x_turns, rotation_y_turns, rotation_z_turns
from tools.native_oracle import DynoOracle


OUTPUT = 0x71001000
BUILDERS = ((0x6F1530, rotation_x_turns),
            (0x6F1590, rotation_y_turns),
            (0x6F15F0, rotation_z_turns))


def verify(executable, cases=512):
    if type(cases) is not int or not 1 <= cases <= 10_000:
        raise ValueError('cases must be between 1 and 10000')
    oracle = DynoOracle(executable)
    rng = random.Random(0x6F1530)
    turns_set = (0., 0.125, 0.25, -0.25, 0.5, -0.5)
    compared = 0
    for entry, builder in BUILDERS:
        for case in range(cases):
            turns = turns_set[case % len(turns_set)] if case < len(turns_set) else rng.uniform(-10., 10.)
            expected = builder(turns)
            oracle._reset()
            oracle.cpu.mem_write(OUTPUT, bytes(36))
            turn_bits = struct.unpack('<I', struct.pack('<f', turns))[0]
            oracle.call(entry, (OUTPUT, turn_bits), instruction_limit=100_000)
            actual = struct.unpack('<9f', oracle.cpu.mem_read(OUTPUT, 36))
            for index, (got, want) in enumerate(zip(actual, expected)):
                if abs(got - want) > 2e-7:
                    raise AssertionError(
                        f'{entry:#x} case {case}, matrix[{index}]: '
                        f'native={got}, model={want}, turns={turns}')
            compared += 1
    return {'entries': [hex(entry) for entry, _ in BUILDERS],
            'cases_per_entry': cases, 'native_matching_matrices': compared,
            'scope': 'X/Y/Z rotation matrices from turn values; float results use absolute tolerance 2e-7'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    parser.add_argument('--cases', type=int, default=512)
    args = parser.parse_args()
    print(json.dumps(verify(args.executable, args.cases)))


if __name__ == '__main__':
    main()
