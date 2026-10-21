"""Compare scalar 0x6efcd0 getstate selectors with native execution."""
import argparse
import random
import struct
from pathlib import Path

from client.mouse_state_get import MouseScalarState, get_mouse_scalar_state
from tools.native_oracle import DynoOracle


ACCESS_MODE = 0x008C8914
STATE8 = 0x008C8918
STATE9 = 0x008C891C


def verify(executable, cases=512):
    oracle = DynoOracle(executable)
    cpu = oracle.cpu
    rng = random.Random(0x6EFCD0)
    for index in range(cases):
        values = tuple(rng.getrandbits(32) for _ in range(3))
        for address, value in zip((ACCESS_MODE, STATE8, STATE9), values):
            cpu.mem_write(address, struct.pack('<I', value))
        state = MouseScalarState(*values)
        for selector in (7, 8, 9):
            expected = get_mouse_scalar_state(selector, state)
            oracle.call(0x006EFCD0, (selector,), instruction_limit=100)
            actual = cpu.reg_read(oracle.reg.UC_X86_REG_EAX)
            if actual != expected:
                raise AssertionError(f'case={index} selector={selector}: '
                                     f'native={actual:#x}, python={expected:#x}')
    return cases * 3


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', type=Path)
    parser.add_argument('--cases', type=int, default=512)
    args = parser.parse_args()
    print(f'0x6efcd0 scalar getters match {verify(args.executable, args.cases)} '
          'original selector calls')


if __name__ == '__main__':
    main()
