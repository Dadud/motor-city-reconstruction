"""Compare complete original startup surface factor and 135-point table."""
import argparse
import itertools
import json
import struct

from client.startup_resistance import startup_surface_factor, startup_resistance_table
from tools.native_oracle import DynoOracle


def factor_cases():
    return itertools.product((0, 1, 2, 3, 4, 5, 6, 0xffffffff),
                             (-10., -0., 0., .99999994, 1., 1.00000012, 33., 134., 500.))


def table_cases():
    return itertools.product((0., 575., 1000., 1800.), (0., .22, .45), (0., 1.5, 2.75),
                             (0, 2, 3, 5, 0xffffffff))


def verify(executable):
    oracle = DynoOracle(executable)
    cpu = oracle.cpu
    result = oracle.inputs + 0x9000
    # Store the x87 return as a double, then jump to the bounded stop.
    cpu.mem_write(oracle.stub, b'\xdd\x1d' + struct.pack('<I', result) +
                  b'\xe9' + struct.pack('<i', oracle.stop - (oracle.stub + 11)))
    factors = tables = 0
    for selector, speed in factor_cases():
        oracle._reset()
        stack = cpu.reg_read(oracle.reg.UC_X86_REG_ESP)
        cpu.mem_write(stack, struct.pack('<IIf', oracle.stub, selector, speed))
        oracle._run(0x53e620, oracle.stop, count=500)
        actual = bytes(cpu.mem_read(result, 8))
        expected = struct.pack('<d', startup_surface_factor(selector, speed))
        if actual != expected:
            raise AssertionError(('surface', selector, speed, actual.hex(), expected.hex()))
        factors += 1
    for mass, coefficient, area, selector in table_cases():
        oracle._reset()
        stack = cpu.reg_read(oracle.reg.UC_X86_REG_ESP)
        # Sentinel bytes test the complete output extent, not just the values.
        cpu.mem_write(result - 4, b'\xa5' * (135 * 4 + 8))
        cpu.mem_write(stack, struct.pack('<IIfffI', oracle.stop, result, mass,
                                         coefficient, area, selector))
        oracle._run(0x550ed0, oracle.stop, count=20000)
        actual = bytes(cpu.mem_read(result - 4, 135 * 4 + 8))
        expected = b'\xa5' * 4 + struct.pack('<135f', *startup_resistance_table(
            mass, coefficient, area, selector)) + b'\xa5' * 4
        if actual != expected:
            raise AssertionError(('table', mass, coefficient, area, selector))
        tables += 1
    return dict(surface_calls=factors, table_calls=tables, table_entries=tables*135,
                maximum_absolute_error=0, integrated_road_load_verified=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    print(json.dumps(verify(parser.parse_args().executable)))
