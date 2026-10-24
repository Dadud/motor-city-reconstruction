"""Compare 0x6aa840's default byte-fold mode with the installed original."""
import json
import random

from client.string_compare import compare_config_names
from tools.native_oracle import DynoOracle


def _names(count):
    rng = random.Random(0x6aa840)
    for index in range(count):
        if index < 8:
            left = (b'garage', b'GARAGE', b'A', b'a', b'alpha', b'beta',
                    b'\x80x', b'\xff')[index]
            right = (b'GARAGE', b'garage', b'a', b'A', b'Beta', b'ALPHA',
                     b'\x81x', b'\x00')[index]
        else:
            left = bytes(rng.randrange(1, 256) for _ in range(rng.randrange(0, 300)))
            right = bytes(rng.randrange(1, 256) for _ in range(rng.randrange(0, 300)))
        yield left + b'\0', right + b'\0'


def verify(executable, cases=1024):
    oracle = DynoOracle(executable)
    cpu = oracle.cpu
    left_ptr, right_ptr = oracle.inputs + 0x100, oracle.inputs + 0x500
    cpu.mem_write(0x00b2b5b4, b'\0')  # select the observed default non-locale mode
    for index, (left, right) in enumerate(_names(cases)):
        cpu.mem_write(left_ptr, left)
        cpu.mem_write(right_ptr, right)
        oracle.call(0x6aa840, (left_ptr, right_ptr), instruction_limit=10000)
        actual = cpu.reg_read(oracle.reg.UC_X86_REG_EAX)
        actual = actual - 0x100000000 if actual & 0x80000000 else actual
        expected = compare_config_names(left, right)
        if actual != expected:
            raise AssertionError((index, left.hex(), right.hex(), actual, expected))
    return {'cases': cases, 'result': 'exact',
            'scope': 'original 0x6aa840 with global locale-mode flag zero; NUL-terminated byte strings including high bytes and up to 299-byte names'}


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    parser.add_argument('--cases', type=int, default=1024)
    args = parser.parse_args()
    print(json.dumps(verify(args.executable, args.cases)))
