"""Complete original wind function and trig helpers; virtual mode query supplied."""
import argparse
import itertools
import json
import math
import struct
from client.wind import WindState, calculate_wind
from tools.native_oracle import DynoOracle


def cases():
    counters = (-0x80000000, -65537, -1, 0, 1, 63, 64, 1919, 1920, 2400, 65537, 0x7fffffff)
    seeds = (-0x80000000, -361, -360, -16, -15, -1, 0, 1, 2, 3, 14, 15, 359, 360, 361, 0x7fffffff)
    directions = ((0., 1., 1.), (1., 0., 0.), (-1., 0., 1.), (0., 0., -1.), (.3, .2, -.7))
    matrices = ((1., 0., 0., 0., 1., 0., 0., 0., 1.), (.8, 0., -.6, 0., 1., 0., .6, 0., .8),
                (.3, -.2, .7, .1, .4, -.3, -.8, .6, .5))
    for counter, seed, direction, matrix, disabled in itertools.product(counters, seeds, directions, matrices, (False, True)):
        yield WindState(counter, seed, direction, matrix, disabled)


def verify(executable):
    from unicorn import UC_HOOK_CODE
    oracle = DynoOracle(executable)
    cpu, reg = oracle.cpu, oracle.reg
    owner, output, track, interface, vtable = (oracle.inputs + off for off in (0, 0x3000, 0x4000, 0x5000, 0x5100))
    query = oracle.stub + 0x100
    cpu.mem_write(interface, struct.pack('<I', vtable))
    cpu.mem_write(vtable+0x10, struct.pack('<I', query))
    cpu.mem_write(0xa65bd0, struct.pack('<I', interface))
    cpu.mem_write(0x97c38c, struct.pack('<I', track))
    cpu.mem_write(0x9aaa78, struct.pack('<i', 2))
    calls = []
    disabled = False
    def mode(cpu, address, size, user):
        stack = cpu.reg_read(reg.UC_X86_REG_ESP)
        ret, operation, argument = struct.unpack('<III', cpu.mem_read(stack, 12))
        if operation != 1 or argument != 0 or cpu.reg_read(reg.UC_X86_REG_ECX) != interface:
            raise AssertionError('wind interface query arguments')
        calls.append((operation, argument))
        cpu.reg_write(reg.UC_X86_REG_EAX, int(disabled))
        cpu.reg_write(reg.UC_X86_REG_ESP, stack+12)
        cpu.reg_write(reg.UC_X86_REG_EIP, ret)
    cpu.hook_add(UC_HOOK_CODE, mode, begin=query, end=query)
    maximum = 0.
    count = 0
    for state in cases():
        oracle._reset()
        calls.clear()
        disabled = state.disabled
        image = bytearray([0xa5])*0x1d00
        struct.pack_into('<9f', image, 0x9c, *state.world_to_body)
        track_image = bytearray([0x5a])*0x200
        struct.pack_into('<3f', track_image, 0x18+2*0x54, *state.track_direction)
        cpu.mem_write(owner, bytes(image))
        cpu.mem_write(track, bytes(track_image))
        cpu.mem_write(output, bytes([0xa5])*20)
        cpu.mem_write(0xaa456c, struct.pack('<i', state.simulation_counter))
        cpu.mem_write(0x9aa9ac, struct.pack('<i', state.weather_seed))
        stack = oracle.frame-0x1000
        cpu.mem_write(stack, struct.pack('<III', oracle.stop, output+4, owner))
        cpu.reg_write(reg.UC_X86_REG_ESP, stack)
        oracle._run(0x536fb0, oracle.stop, count=50000)
        expected = calculate_wind(state)
        actual = struct.unpack('<3f', cpu.mem_read(output+4, 12))
        for a, b in zip(actual, expected.body_velocity):
            error = abs(a-b)
            if not math.isfinite(a) or error > max(2e-6, abs(a)*4e-7):
                raise AssertionError((count, state, actual, expected, error))
            maximum = max(maximum, error)
        if cpu.reg_read(reg.UC_X86_REG_EAX) != int(expected.present):
            raise AssertionError('wind present return')
        if bytes(cpu.mem_read(owner, len(image))) != image or bytes(cpu.mem_read(track, len(track_image))) != track_image:
            raise AssertionError('unexpected owner or track write')
        if bytes(cpu.mem_read(output, 4))+bytes(cpu.mem_read(output+16, 4)) != bytes([0xa5])*8 or calls != [(1, 0)]:
            raise AssertionError('output boundary or query order')
        count += 1
    return {'cases': count, 'maximum_absolute_error': maximum, 'scope': 'complete 536fb0 with actual atan/sin/cos; only virtual mode query supplied'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    print(json.dumps(verify(parser.parse_args().executable)))
