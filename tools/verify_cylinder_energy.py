"""Compare recovered energy terms with a user-supplied verified executable.

Requires optional Unicorn. Executes only the bounded polynomial range in an
emulator; no game entry point, operating-system services or network are used.
"""
import argparse
from dataclasses import astuple
import json
import struct

from client.dyno import _SOURCE_SHA256
from client.thermodynamics import cylinder_energy_terms
from tools.native_oracle import DynoOracle


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    args = parser.parse_args()
    oracle = DynoOracle(args.executable)
    for index in range(1, 10001):
        temperature = index*.9999
        oracle._reset()
        oracle.cpu.mem_write(oracle.frame-0x1c, struct.pack('<f', temperature))
        oracle._run(0x47ae8f, 0x47af0b, timeout=0, count=100)
        expected = [bytes(oracle.cpu.mem_read(oracle.frame-offset, 4))
                    for offset in (0x90, 0x30)]
        actual = [struct.pack('<f', value)
                  for value in astuple(cylinder_energy_terms(temperature))]
        if actual != expected:
            raise AssertionError(f'energy terms differ at temperature {temperature}')
    print(json.dumps({'source_sha256': _SOURCE_SHA256,
                      'range': '0x47ae8f-0x47af0b', 'temperatures': 10000,
                      'exact_float32_fields': 20000,
                      'evidence_type': 'bounded x86 emulation'}, indent=2))


if __name__ == '__main__':
    main()
