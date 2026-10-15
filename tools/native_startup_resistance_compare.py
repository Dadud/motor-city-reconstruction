"""Compare all native startup resistance output bits with the Python port."""
import argparse
import json
import struct
import subprocess

from client.startup_resistance import startup_resistance_table, startup_surface_factor
from tools.startup_resistance_oracle import factor_cases, table_cases


def bits(value):
    return struct.unpack('<I', struct.pack('<f', value))[0]


def verify(runner):
    lines, expected = [], []
    for selector, speed in factor_cases():
        lines.append(f'0 {selector} {bits(speed)}')
        expected.append(struct.unpack('<Q', struct.pack('<d', startup_surface_factor(selector, speed))))
    factors = len(lines)
    for mass, coefficient, area, selector in table_cases():
        lines.append(f'1 {selector} {bits(mass)} {bits(coefficient)} {bits(area)}')
        expected.append(tuple(map(bits, startup_resistance_table(mass, coefficient, area, selector))))
    process = subprocess.run([str(runner)], input='\n'.join(lines)+'\n', text=True,
                             capture_output=True, check=True, timeout=30)
    observed = [tuple(map(int, line.split())) for line in process.stdout.splitlines()]
    if observed != expected:
        raise AssertionError('native startup resistance output bits differ')
    return dict(surface_cases=factors, table_cases=len(lines)-factors, maximum_absolute_error=0)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('runner')
    print(json.dumps(verify(parser.parse_args().runner)))
