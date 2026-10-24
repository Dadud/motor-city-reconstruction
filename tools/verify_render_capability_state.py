"""Compare three renderer-global setters with their original functions."""
import argparse
import json
import random
import struct

from client.render_state import (RenderCapabilityState, set_capability_2,
                                 set_capability_4, set_vertex_format_cache)
from tools.native_oracle import DynoOracle


GLOBALS = {0xB368C4: 'capability_4', 0xB368C8: 'capability_2',
           0xB368E8: 'capability_4_dirty', 0xB368EC: 'capability_2_dirty',
           0x8C89F0: 'mode_cache', 0x8C89F8: 'vertex_format_cache'}
CASES = ((0x6F19D0, set_capability_4), (0x6F1A00, set_capability_2),
         (0x6F1A70, set_vertex_format_cache))


def verify(executable, cases=512):
    if type(cases) is not int or not 1 <= cases <= 10_000:
        raise ValueError('cases must be between 1 and 10000')
    oracle = DynoOracle(executable)
    rng = random.Random(0x6F19D0)
    for entry, setter in CASES:
        for case in range(cases):
            words = {name: rng.getrandbits(32) for name in set(GLOBALS.values())}
            if case % 4 == 0:
                value = 0
            elif case % 4 == 1:
                value = 1
            else:
                value = rng.getrandbits(32)
            state = RenderCapabilityState(**words)
            expected_old, expected_state = setter(state, value)
            oracle._reset()
            for address, name in GLOBALS.items():
                oracle.cpu.mem_write(address, struct.pack('<I', words[name]))
            oracle.call(entry, (value,), instruction_limit=100_000)
            actual_old = oracle.cpu.reg_read(oracle.reg.UC_X86_REG_EAX)
            if actual_old != expected_old:
                raise AssertionError(
                    f'{entry:#x} case {case}: old={actual_old:#x}, expected={expected_old:#x}')
            for address, name in GLOBALS.items():
                actual = struct.unpack('<I', oracle.cpu.mem_read(address, 4))[0]
                expected = getattr(expected_state, name)
                if actual != expected:
                    raise AssertionError(
                        f'{entry:#x} case {case}, {name}: '
                        f'native={actual:#x}, expected={expected:#x}')
    return {'entries': [hex(entry) for entry, _ in CASES],
            'cases_per_entry': cases, 'native_calls': cases * len(CASES),
            'scope': 'setter return values and all six affected renderer globals'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    parser.add_argument('--cases', type=int, default=512)
    args = parser.parse_args()
    print(json.dumps(verify(args.executable, args.cases)))


if __name__ == '__main__':
    main()
