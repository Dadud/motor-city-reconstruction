"""Execute complete original load correction with no substituted calls."""
import argparse
import itertools
import json
import struct

from client.load_transfer import LoadTransferInput, transfer_load
from client.tire_response import f32
from tools.native_oracle import DynoOracle


def cases():
    threshold = f32(0.1962)
    for loads, attitude, longitudinal, lateral, speed in itertools.product(
            ((2000, 2100, 1500, 1600), (1, 100, 1, 100)),
            (-0.25001, -0.25, 0, 0.25, 0.25001),
            (-20, -threshold, 0, threshold, 20),
            (-15, -threshold, 0, threshold, 15),
            (-6.001, -6, 0, 6, 6.001)):
        yield LoadTransferInput(loads, attitude, longitudinal, lateral, speed,
                                1450, 2.7, 1.6, 1.7, 0.55, 0.12, 0.18)


def verify(executable):
    o = DynoOracle(executable)
    cpu, reg = o.cpu, o.reg
    owner, config = o.inputs, o.inputs + 0x3000
    offsets = (0x6d0, 0x7dc, 0x9f4, 0x8e8)
    count, maximum_error = 0, 0.0
    for state in cases():
        o._reset()
        image = bytearray([0xa5]) * 0x1d00
        struct.pack_into('<I', image, 0x1c94, config)
        values = [(offset, load) for offset, load in zip(offsets, state.loads)]
        values += [(0xc00, state.attitude), (0xa38, state.longitudinal_acceleration),
                   (0xa30, state.lateral_acceleration), (0xa2c, state.speed),
                   (0x18ec, state.front_offset), (0x18f0, state.rear_offset)]
        for offset, value in values:
            struct.pack_into('<f', image, offset, value)
        cpu.mem_write(owner, bytes(image))
        configuration = bytearray([0x5a]) * 0x100
        for offset, value in ((0x20, state.mass), (0x2c, state.wheelbase),
                              (0x30, state.front_track), (0x34, state.rear_track),
                              (0x38, state.height_parameter)):
            struct.pack_into('<f', configuration, offset, value)
        cpu.mem_write(config, bytes(configuration))
        stack = o.frame - 0x1000
        cpu.mem_write(stack, struct.pack('<II', o.stop, owner))
        cpu.reg_write(reg.UC_X86_REG_ESP, stack)
        o._run(0x53e680, o.stop, count=20000)
        actual = bytes(cpu.mem_read(owner, len(image)))
        expected = transfer_load(state)
        for offset, target in zip(offsets, expected):
            value = struct.unpack_from('<f', actual, offset)[0]
            error = abs(value - target)
            if error > max(0.00025, abs(value)*3e-7):
                raise AssertionError((count, state, offset, value, target))
            maximum_error = max(maximum_error, error)
            image[offset:offset+4] = actual[offset:offset+4]
        if actual != image or cpu.mem_read(config, len(configuration)) != configuration:
            raise AssertionError('unexpected owner/configuration mutation')
        count += 1
    return {'cases': count, 'maximum_absolute_error': maximum_error,
            'scope': 'complete 0x53e680, no substituted calls, synthetic isolated owner/component state'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    print(json.dumps(verify(parser.parse_args().executable)))
