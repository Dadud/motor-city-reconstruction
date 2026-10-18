"""Original-comparison oracle for the global instance accessor 0x405900.

The body reads two process globals and returns one of them, so the oracle
supplies both and reads the result straight out of the original's EAX. The
native harness receives the same pair and must return the same address.
"""
import argparse
import json
import struct

from tools.native_oracle import DynoOracle

ENTRY = 0x405900
PRIMARY = 0x9aaa98
FALLBACK = 0x988e38


def cases():
    """Both branches, the zero case and addresses that are not pointers."""
    values = (0, 1, 0x70a80000, 0x1234, 0x4321, 0x80000000, 0xffffffff)
    for primary in values:
        for fallback in values:
            yield primary, fallback


def verify(executable):
    oracle = DynoOracle(executable)
    oracle.cpu.mem_map(0, 0x1000)  # inert FS:[0] SEH chain
    expected = []
    for primary, fallback in cases():
        oracle._reset()
        oracle.cpu.mem_write(PRIMARY, struct.pack('<I', primary))
        oracle.cpu.mem_write(FALLBACK, struct.pack('<I', fallback))
        # The body is a leaf that ends in RET, so the oracle plants its own
        # return address instead of calling through the original.
        stack = oracle.frame-0x1000
        oracle.cpu.mem_write(stack, struct.pack('<I', oracle.stop))
        oracle.cpu.reg_write(oracle.reg.UC_X86_REG_ESP, stack)
        oracle._run(ENTRY, oracle.stop, timeout=0, count=64)
        actual = oracle.cpu.reg_read(oracle.reg.UC_X86_REG_EAX)
        expected.append((primary, fallback, actual))
    return expected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    parsed = parser.parse_args()
    rows = verify(parsed.executable)
    wrong = [(p, f, a) for p, f, a in rows
             if a != (p if p != 0 else f)]
    if wrong:
        raise AssertionError(f'original did not follow the selection rule: {wrong[:4]}')
    print(json.dumps(dict(cases=len(rows), exact_output_bits=True,
                          scope='0x405900 whole body; both globals supplied; '
                                'returned address exact')))


if __name__ == '__main__':
    main()