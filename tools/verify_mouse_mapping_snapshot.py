"""Compare the 0x4ad869 mapped-button snapshot store with the original."""
import argparse
import random
import struct
from pathlib import Path

from client.mouse_mapping_snapshot import MouseMappingSource, publish_mouse_mapping_snapshot
from tools.native_oracle import DynoOracle


SOURCE = 0x7100C000
ENTRY = 0x004AD869
STOP = 0x004AD8C6
SOURCE_WORDS = (0x009ABB20, 0x009ABB24, 0x009ABB1C, 0x009ABB28)
DESTINATIONS = (0x009E1654, 0x009E1648, 0x009E1658, 0x009E164C,
                0x009E165C, 0x009E1668, 0x009E1650)


def compare(executable, cases=1024):
    oracle = DynoOracle(executable)
    cpu, reg = oracle.cpu, oracle.reg
    rng = random.Random(0x4ad869)
    for case in range(cases):
        oracle._reset()
        record = bytearray(rng.randbytes(0x13))
        values = tuple(rng.getrandbits(32) for _ in range(4))
        cpu.mem_write(SOURCE, bytes(record))
        for address, value in zip(SOURCE_WORDS, values):
            cpu.mem_write(address, struct.pack('<I', value))
        cpu.reg_write(reg.UC_X86_REG_EDI, SOURCE)
        expected = publish_mouse_mapping_snapshot(MouseMappingSource(bytes(record), *values))
        cpu.emu_start(ENTRY, STOP, timeout=0, count=100)
        if cpu.reg_read(reg.UC_X86_REG_EIP) != STOP:
            raise AssertionError(f'case {case}: native range did not stop at {STOP:#x}')
        actual = tuple(struct.unpack('<I', cpu.mem_read(address, 4))[0]
                       for address in DESTINATIONS)
        wanted = (expected.value_9e1654, expected.value_9e1648,
                  expected.value_9e1658, expected.value_9e164c,
                  expected.value_9e165c, expected.value_9e1668,
                  expected.value_9e1650)
        if actual != wanted:
            raise AssertionError(f'case {case}: native {actual!r} != source {wanted!r}')
    return cases


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', type=Path)
    parser.add_argument('--cases', type=int, default=1024)
    args = parser.parse_args()
    count = compare(args.executable, args.cases)
    print(f'mouse mapping snapshot stores matched {count} original instruction ranges')


if __name__ == '__main__':
    main()
