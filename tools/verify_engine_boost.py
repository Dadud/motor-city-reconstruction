"""Compare the recovered boost helper against original stored state writes."""
import argparse
import json
from pathlib import Path
import struct

from client.engine_boost import update_boost_state
from tools.native_oracle import DynoOracle


def fixture(mode, rpm=5000.):
    configuration = bytearray(1004)
    struct.pack_into('<h', configuration, 0x3c4, mode)
    for offset, value in ((0x3c8, 1.4), (0x3cc, .8), (0x3d0, 100.),
                          (0x3d4, 2.), (0x3d8, 8.), (0x3dc, 10.),
                          (0x3e0, .5), (0x3e4, .8), (1000, 100.)):
        struct.pack_into('<f', configuration, offset, value)
    state = bytearray(0x10c)
    for offset, value in ((0xf0, 70.), (0xf4, 400.), (0xf8, 540.),
                          (0xfc, rpm), (0x100, 2.)):
        struct.pack_into('<f', state, offset, value)
    return bytes(configuration), bytes(state)


def verify(executable):
    oracle = DynoOracle(executable)
    results = []
    cases = [(0, 5000.)] + [(mode, rpm) for mode, rpms in (
        (1, (2000., 5000., 10000.)), (2, (5000., 10000.)),
        (3, (2000., 5000., 10000.))) for rpm in rpms]
    for mode, rpm in cases:
        configuration, state = fixture(mode, rpm)
        oracle._reset()
        oracle.cpu.mem_write(oracle.inputs, configuration)
        oracle.cpu.mem_write(oracle.inputs + 0x2000, state)
        oracle.call(0x586730, (oracle.inputs, 0, oracle.inputs + 0x2000))
        original = bytes(oracle.cpu.mem_read(oracle.inputs + 0x2000, len(state)))
        authored = update_boost_state(configuration, state)
        differences = [offset for offset, (left, right) in enumerate(zip(original, authored))
                       if left != right]
        results.append({
            'mode': mode,
            'rpm': rpm,
            'equal': not differences,
            'differing_byte_offsets': differences,
            'original_written_fields': {
                hex(offset): original[offset:offset + 4].hex()
                for offset in (0xf8, 0x100, 0x104, 0x108)
            },
        })
    return {
        'modes': results,
        'scope': ('Nine synthetic scratch/configuration states: mode 0 at 5000 RPM; '
                  'modes 1 and 3 at 2000, 5000, and 10000 RPM; mode 2 at 5000 and '
                  '10000 RPM. Mode 2 at 2000 RPM enters an unsupported native domain.'),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', type=Path)
    args = parser.parse_args()
    result = verify(args.executable)
    print(json.dumps(result, indent=2))
    expected_differences = {
        (1, 2000.): [0xf8],
        (2, 10000.): [0x108],
        (3, 2000.): [0x104, 0x105, 0x108, 0x109],
        (3, 5000.): [0x104, 0x105, 0x108, 0x109],
        (3, 10000.): [0x100, 0x104, 0x108, 0x109],
    }
    for case in result['modes']:
        observed = case['differing_byte_offsets']
        expected = expected_differences.get((case['mode'], case['rpm']), [])
        if observed != expected:
            raise SystemExit(f"unexpected native mismatch: mode={case['mode']} "
                             f"rpm={case['rpm']} offsets={observed}; expected={expected}")


if __name__ == '__main__':
    main()
