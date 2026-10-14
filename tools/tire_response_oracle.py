"""Bounded complete original wheel response functions using synthetic tables."""
import argparse
import itertools
import json
import math
import struct

from client.tire_response import WheelCurveInput, wheel_response, f32
from tools.native_oracle import DynoOracle


def cases():
    tables = (tuple(i * 37.25 for i in range(26)),
              tuple((i % 5 - 2) * 123.5 for i in range(26)))
    for table, slip, load, angle, secondary, alternate in itertools.product(
            tables, (-0.2, -25/180, -4.5/180, -0.0, 0.0, 0.001, 4.5/180, 25/180, 0.2),
            (0, 1000, 3999.9995, 4000, 4000.0005, 8000, 14000, 30000),
            (-0.003, 0.0, 0.003), (False, True), (False, True)):
        yield table, 0.021, WheelCurveInput(slip, angle, load, 0.8), secondary, alternate


def verify(executable):
    oracle = DynoOracle(executable)
    cpu, reg = oracle.cpu, oracle.reg
    table_address, wheel_address = oracle.inputs, oracle.inputs + 0x200
    wrappers = {}
    for secondary, entry in ((False, 0x53f630), (True, 0x53f830)):
        address = oracle.stub + (0x100 if secondary else 0)
        wrapper = b'\xe8' + struct.pack('<i', entry - (address + 5))
        wrapper += b'\xdd\x1d' + struct.pack('<I', oracle.inputs + 0x400)
        cpu.mem_write(address, wrapper)
        wrappers[secondary] = address
    count, maximum_error = 0, 0.0
    for table, coefficient, wheel, secondary, alternate in cases():
        oracle._reset()
        cpu.mem_write(table_address, struct.pack('<26f', *table))
        cpu.mem_write(wheel_address, bytes(0x100))
        for offset, value in ((4, wheel.slip_angle), (8, wheel.secondary_angle),
                              (0xd4, wheel.normal_load), (0xf8, wheel.surface_multiplier)):
            cpu.mem_write(wheel_address + offset, struct.pack('<f', value))
        cpu.mem_write(0xa384c8, struct.pack('<I', int(alternate)))
        # Original function returns on x87. Store it as its wheel-update caller does.
        stack = oracle.frame - 0x1000
        # The wrapper CALL supplies the return address before these cdecl args.
        cpu.mem_write(stack, struct.pack('<I f I', table_address, coefficient, wheel_address))
        cpu.reg_write(reg.UC_X86_REG_ESP, stack)
        # Stop immediately after storing the result; no wrapper RET through args.
        address = wrappers[secondary]
        oracle._run(address, address + 11, count=20000)
        actual = f32(struct.unpack('<d', cpu.mem_read(oracle.inputs + 0x400, 8))[0])
        expected = wheel_response(table, coefficient, wheel, secondary=secondary, alternate_load=alternate)
        error = abs(actual - expected)
        tolerance = max(0.00025, abs(actual) * 3e-7)
        if not math.isfinite(actual) or error > tolerance:
            raise AssertionError((count, wheel, secondary, alternate, actual, expected, error))
        maximum_error = max(maximum_error, error)
        count += 1
    return {'cases': count, 'maximum_absolute_error': maximum_error,
            'scope': 'complete 0x53f630/0x53f830; synthetic 26-knot tables; original floor helper; no host calls or sockets'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    print(json.dumps(verify(parser.parse_args().executable)))
