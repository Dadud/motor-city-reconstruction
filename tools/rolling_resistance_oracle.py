"""Complete original resistance helper with substituted mode predicate only."""
import argparse
import itertools
import json
import struct

from client.rolling_resistance import ResistanceWheel, rolling_resistance
from tools.native_oracle import DynoOracle


def verify(executable):
    from unicorn import UC_HOOK_CODE
    o = DynoOracle(executable)
    cpu, reg = o.cpu, o.reg
    owner, config = o.inputs, o.inputs + 0x3000
    state = {}

    def predicate(_cpu, address, _size, _user):
        if address != 0x55fc30:
            return
        state['calls'] += 1
        stack = cpu.reg_read(reg.UC_X86_REG_ESP)
        ret = struct.unpack('<I', cpu.mem_read(stack, 4))[0]
        cpu.reg_write(reg.UC_X86_REG_EAX, int(state['mode']))
        cpu.reg_write(reg.UC_X86_REG_ESP, stack + 4)
        cpu.reg_write(reg.UC_X86_REG_EIP, ret)

    cpu.hook_add(UC_HOOK_CODE, predicate)
    count, max_error = 0, 0.0
    for speed, disabled, mode, alternate, angle, contact_mask, rolling in itertools.product(
            (-20, -2, -1.9999, 0, 1.9999, 2, 20), (False, True), (False, True),
            (False, True), (0, 0.1), (0, 5, 15), (-2, 0.5, 0.5001, 2)):
        o._reset()
        image = bytearray([0xa5]) * 0x1d00
        struct.pack_into('<I', image, 0x1c94, config)
        struct.pack_into('<I', image, 0x474, 0x200 if disabled else 0)
        for offset, value in ((0xa2c, speed), (0xd00, 0.3), (0xd04, -0.1), (0xc00, angle)):
            struct.pack_into('<f', image, offset, value)
        wheels = []
        for index, surface in enumerate((2, 3, 5, 0)):
            base = 0x600 + index * 0x10c
            wheel = ResistanceWheel((index-1)*0.01, surface, 0 if index == 3 else 1500+index*500,
                                    rolling, 2, bool(contact_mask & (1 << index)), 100+index)
            wheels.append(wheel)
            for offset, value in ((0, wheel.slip_angle), (0xd0, wheel.normal_load),
                                  (0x78, rolling), (0xb8, 2), (0xd4, wheel.longitudinal_force)):
                struct.pack_into('<f', image, base + offset, value)
            struct.pack_into('<I', image, base+0xc8, surface)
            image[base+0xe8] = int(wheel.contact)
        cpu.mem_write(owner, bytes(image))
        cpu.mem_write(config, bytes(0x300))
        for offset, value in ((0x13c, 1.2), (0x240, 0.8)):
            cpu.mem_write(config+offset, struct.pack('<f', value))
        cpu.mem_write(0xa384c8, struct.pack('<I', int(alternate)))
        state.update(mode=mode, calls=0)
        stack = o.frame - 0x1000
        cpu.mem_write(stack, struct.pack('<II', o.stop, owner))
        cpu.reg_write(reg.UC_X86_REG_ESP, stack)
        o._run(0x53e3d0, o.stop, count=20000)
        # Save ST0 without executing a host boundary.
        cpu.mem_write(o.stub, b'\xdd\x1d' + struct.pack('<I', o.inputs+0x4000))
        o._run(o.stub, o.stub+6, count=1)
        actual_return = struct.unpack('<d', cpu.mem_read(o.inputs+0x4000, 8))[0]
        expected = rolling_resistance(wheels, speed, 1.2, 0.8, 0.3, -0.1, angle,
            disabled_flag=disabled, mode_predicate=mode, alternate=alternate)
        actual = bytes(cpu.mem_read(owner, len(image)))
        for index, wheel in enumerate(expected.wheels):
            offset = 0x600 + index*0x10c + 0xd4
            value = struct.unpack_from('<f', actual, offset)[0]
            error = abs(value - wheel.longitudinal_force)
            if error > max(0.00025, abs(value)*3e-7):
                raise AssertionError((count, index, value, wheel))
            max_error = max(max_error, error)
            image[offset:offset+4] = actual[offset:offset+4]
        if actual != image:
            raise AssertionError('unexpected owner-state mutation')
        if abs(actual_return - expected.last_contribution) > max(0.00025, abs(actual_return)*3e-7):
            raise AssertionError((count, actual_return, expected.last_contribution))
        if state['calls'] != int(abs(speed) >= 2 and not disabled):
            raise AssertionError('mode predicate call gate mismatch')
        count += 1
    return {'cases': count, 'maximum_force_error': max_error,
            'scope': 'complete 0x53e3d0, original turn cosine, synthetic wheel/component state; mode predicate substituted'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    print(json.dumps(verify(parser.parse_args().executable)))
