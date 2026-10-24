"""Compare normalized random fraction with original routine 0x6f2c90."""
import argparse
import json
import random
import struct

from client.random_state import RandomState
from tools.native_oracle import DynoOracle


STATE_WORDS = (0x8c89d0, 0x8c89d4, 0x8c89d8,
               0x8c89dc, 0x8c89e0, 0x8c89e4)


def verify(executable, cases=1024):
    if type(cases) is not int or not 1 <= cases <= 4096:
        raise ValueError('cases must be between 1 and 4096')
    oracle = DynoOracle(executable)
    rng = random.Random(0x6F2C90)
    seeds = [(0xf22d0e56, 0x883126e9, 0xc624dd2f,
              0x0702c49c, 0x9e353f7d, 0x6fdf3b64)]
    seeds.extend(tuple(rng.getrandbits(32) for _ in range(6))
                 for _ in range(cases - 1))
    capture = oracle.inputs + 0x700
    fstp_float = b'\xd9\x1d' + struct.pack('<I', capture)
    for index, initial in enumerate(seeds):
        for address, word in zip(STATE_WORDS, initial):
            oracle.cpu.mem_write(address, struct.pack('<I', word))
        oracle.call(0x6f2c90, tail=fstp_float)
        actual_bits = struct.unpack('<I', oracle.cpu.mem_read(capture, 4))[0]

        expected_state = RandomState(initial)
        expected = expected_state.next_unit_fraction()
        expected_bits = struct.unpack('<I', struct.pack('<f', expected))[0]
        if actual_bits != expected_bits:
            raise AssertionError(
                f'case {index}: native={actual_bits:#010x}, '
                f'expected={expected_bits:#010x}, state={initial!r}')
    return {'entry': '0x6f2c90', 'cases': len(seeds),
            'scope': 'exact binary32 capture of low-16-bit random fraction; '
                     'original shared state supplied'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    parser.add_argument('--cases', type=int, default=1024)
    args = parser.parse_args()
    print(json.dumps(verify(args.executable, args.cases)))


if __name__ == '__main__':
    main()
