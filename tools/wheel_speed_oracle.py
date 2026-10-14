"""Complete 0x53e030 comparison, actual original turn sine/cosine helpers."""
import argparse
import itertools
import json
import math
import struct

from client.wheel_speed import WheelSpeedInput, WheelSpeedState, project_wheel_speeds
from tools.native_oracle import DynoOracle


def cases():
    for lateral, longitudinal, yaw, angle, mask in itertools.product(
            (-7, 0, 7), (-20, 0, 20), (-0.3, 0, 0.3), (-0.2, 0, 0.2), range(16)):
        wheels = tuple(WheelSpeedInput(angle * (1 if i % 2 == 0 else -1),
            bool(mask & (1 << i)), (i-1)*3.75, 0.25+i*0.1) for i in range(4))
        yield WheelSpeedState(wheels, lateral, longitudinal, yaw, 1.2, 1.5, 1.6, 1.7)


def verify(executable):
    o = DynoOracle(executable)
    cpu, reg = o.cpu, o.reg
    owner, config = o.inputs, o.inputs+0x3000
    count, maximum_error = 0, 0.0
    for state in cases():
        o._reset()
        image = bytearray([0xa5])*0x1d00
        struct.pack_into('<I', image, 0x1c94, config)
        for offset, value in ((0xa3c, state.lateral_velocity), (0xa44, state.longitudinal_velocity),
                              (0xa58, state.yaw_rate_turns), (0x18b8, state.front_offset),
                              (0x18bc, state.rear_offset)):
            struct.pack_into('<f', image, offset, value)
        for index, wheel in enumerate(state.wheels):
            base = 0x5fc+index*0x10c
            for offset, value in ((0, wheel.angle), (0x7c, wheel.spin_value), (0xbc, wheel.spin_scale)):
                struct.pack_into('<f', image, base+offset, value)
            image[base+0xec] = int(wheel.contact)
        cpu.mem_write(owner, bytes(image))
        configuration = bytearray([0x5a])*0x100
        for offset, value in ((0x30, state.front_track), (0x34, state.rear_track)):
            struct.pack_into('<f', configuration, offset, value)
        cpu.mem_write(config, bytes(configuration))
        stack = o.frame-0x1000
        cpu.mem_write(stack, struct.pack('<II', o.stop, owner))
        cpu.reg_write(reg.UC_X86_REG_ESP, stack)
        o._run(0x53e030, o.stop, count=20000)
        actual = bytes(cpu.mem_read(owner, len(image)))
        for index, expected in enumerate(project_wheel_speeds(state)):
            offset = 0x60c+index*0x10c
            value = struct.unpack_from('<f', actual, offset)[0]
            error = abs(value-expected)
            if not math.isfinite(value) or error > max(0.00025, abs(value)*3e-7):
                raise AssertionError((count, index, value, expected, state))
            maximum_error = max(maximum_error, error)
            image[offset:offset+4] = actual[offset:offset+4]
        if actual != image or cpu.mem_read(config, len(configuration)) != configuration:
            raise AssertionError('unexpected owner/configuration mutation')
        count += 1
    return {'cases': count, 'maximum_absolute_error': maximum_error,
            'scope': 'complete 0x53e030; actual original sine/cosine; all contact masks; no substituted calls'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    print(json.dumps(verify(parser.parse_args().executable)))
