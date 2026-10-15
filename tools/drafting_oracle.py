"""Complete drafting function with original dot/cross/sqrt and cross-car writes."""
import argparse
from dataclasses import replace
import itertools
import json
import math
import struct
from client.drafting import DraftVehicle, calculate_drafting
from tools.native_oracle import DynoOracle


def vehicle(identifier, position=(0., 0., 0.), heading=0., extents=(1., .8, 2.)):
    cosine, sine = math.cos(heading), math.sin(heading)
    return DraftVehicle(identifier, position, (cosine, 0., -sine, 0., 1., 0., sine, 0., cosine), extents,
                        (11., 12., 13.), ((1., 2., 3.),)*4)


def cases():
    own = vehicle(1)
    yield 1, (own,)
    for x, y, z, heading in itertools.product((-3., -1., 0., 1., 3.), (-2., 0., 2.),
            (-13., -12., -8., -4., 0., 4., 8., 12., 13.), (0., .1, .261799, .2618, .3, math.pi)):
        yield 1, (own, vehicle(2, (x, y, z), heading))
    for own_heading, other_heading, extents in itertools.product((-.2, .2, 1.), (-.1, .1, .5), ((.7, .5, 1.), (2., 1.5, 3.))):
        own = vehicle(1, (.3, -.2, 1.1), own_heading, extents)
        for order in ((0, 1, 2), (2, 1, 0), (1, 0, 2)):
            candidates = (own, vehicle(2, (.2, 1., 5.), other_heading), vehicle(3, (-1., 0., 3.), own_heading))
            yield 1, tuple(candidates[i] for i in order)


def encode(car):
    image = bytearray([0xa5])*0x1d00
    struct.pack_into('<3f', image, 8, *car.position)
    struct.pack_into('<9f', image, 0x78, *car.basis)
    struct.pack_into('<3f', image, 0xcc, *car.half_extents)
    struct.pack_into('<3f', image, 0xb8c, *car.wake_origin)
    for i, normal in enumerate(car.wake_normals):
        struct.pack_into('<3f', image, 0xb98+12*i, *normal)
    return image


def verify(executable):
    o = DynoOracle(executable)
    cpu, reg = o.cpu, o.reg
    output = o.inputs+0xf000
    # Store the returned extended factor exactly as its body-resistance consumer.
    code = b'\x68'+struct.pack('<I', o.inputs)
    code += b'\xe8'+struct.pack('<i', 0x536960-(o.stub+len(code)+5))
    code += b'\x83\xc4\x04\xd9\x1d'+struct.pack('<I', output)+b'\xc3'
    cpu.mem_write(o.stub, code)
    maximum = 0.
    counts = {'none': 0, 'inside': 0, 'outside': 0}
    count = 0
    for identifier, cars in cases():
        o._reset()
        # Current owner remains fixed while list order varies independently.
        addresses = {identifier: o.inputs}
        addresses.update({car.identifier: o.inputs+0x2000*(i+1) for i, car in enumerate(c for c in cars if c.identifier != identifier)})
        for car in cars:
            cpu.mem_write(addresses[car.identifier], bytes(encode(car)))
        cpu.mem_write(0x9aaab8, struct.pack('<i', len(cars)))
        table = struct.pack('<'+'I'*len(cars), *(addresses[c.identifier] for c in cars))
        cpu.mem_write(0x98c1e8, table)
        stack = o.frame-0x1000
        cpu.mem_write(stack, struct.pack('<I', o.stop))
        cpu.reg_write(reg.UC_X86_REG_ESP, stack)
        o._run(o.stub, o.stop, count=100000)
        expected = calculate_drafting(identifier, cars)
        actual = struct.unpack('<f', cpu.mem_read(output, 4))[0]
        error = abs(actual-expected.factor)
        if not math.isfinite(actual) or error > max(3e-6, abs(actual)*4e-7):
            raise AssertionError((count, actual, expected, cars))
        maximum = max(maximum, error)
        for car in expected.vehicles:
            actual_image = bytes(cpu.mem_read(addresses[car.identifier], 0x1d00))
            image = encode(car)
            for offset in range(0xb8c, 0xbc8, 4):
                a = struct.unpack_from('<f', actual_image, offset)[0]
                b = struct.unpack_from('<f', image, offset)[0]
                error = abs(a-b)
                if not math.isfinite(a) or error > max(3e-6, abs(a)*4e-7):
                    raise AssertionError((count, car.identifier, hex(offset), a, b, cars))
                maximum = max(maximum, error)
                image[offset:offset+4] = actual_image[offset:offset+4]
            if image != actual_image:
                raise AssertionError('unexpected car state write')
        if bytes(cpu.mem_read(0x98c1e8, len(table))) != table:
            raise AssertionError('vehicle list mutation')
        counts['none' if expected.selected_vehicle is None else 'inside' if expected.inside_wake else 'outside'] += 1
        count += 1
    return {'cases': count, 'branches': counts, 'maximum_absolute_error': maximum,
            'scope': 'complete 536960 and all numeric helpers; ordered vehicle list, factor float32 consumer and complete cross-car images'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    print(json.dumps(verify(parser.parse_args().executable)))
