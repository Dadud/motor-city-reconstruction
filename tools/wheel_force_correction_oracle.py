"""Execute complete original 0x53e130 with bounded CPU-only synthetic state."""
import argparse
import itertools
import json
import struct

from client.wheel_force_correction import ForceCorrectionWheel, correct_wheel_forces
from tools.native_oracle import DynoOracle


def cases():
    for service, other, parking, direction, override, mask, enabled, force in itertools.product(
            (-1, 0, 1), (0, 1), (False, True), (0, 1, 2, 255),
            (False, True), (0, 5, 15), (False, True), (-8000, -500, 0, 500, 8000)):
        wheels = tuple(ForceCorrectionWheel((-1 if i%2 else 1)*12, (i-1)*3, 25-i*20,
            .25+i*.1, (i-1)*400, force, 0 if i == 3 else 2000+i*300,
            .7+i*.1, .5+i*.1, bool(mask & 1<<i), enabled) for i in range(4))
        yield wheels, service, other, parking, direction, override


def verify(executable):
    o = DynoOracle(executable)
    count, maximum = 0, 0.0
    for wheels, service, other, parking, direction, override in cases():
        o._reset()
        image = bytearray([0xa5])*0x1d00
        for offset, value in ((0xa90, service), (0xa94, other)):
            struct.pack_into('<f', image, offset, value)
        for offset, value in ((0xa6b, parking), (0xa69, direction), (0xa88, override)):
            image[offset] = int(value)
        for i, wheel in enumerate(wheels):
            base = 0x5fc+i*0x10c
            for offset, value in ((0x10,wheel.projected_speed),(0x7c,wheel.spin_value),
                    (0x88,wheel.spin_adjustment),(0xbc,wheel.spin_scale),(0xd0,wheel.lateral_force),
                    (0xd8,wheel.longitudinal_force),(0xd4,wheel.normal_load),
                    (0x5c,wheel.primary_coefficient),(0x60,wheel.secondary_coefficient)):
                struct.pack_into('<f', image, base+offset, value)
            image[base+0xec] = int(wheel.contact)
            image[base+0xc5] = int(wheel.correction_enabled)
        o.cpu.mem_write(o.inputs, bytes(image))
        stack = o.frame-0x1000
        o.cpu.mem_write(stack, struct.pack('<II',o.stop,o.inputs))
        o.cpu.reg_write(o.reg.UC_X86_REG_ESP,stack)
        o._run(0x53e130,o.stop,count=10000)
        actual = bytes(o.cpu.mem_read(o.inputs,len(image)))
        expected = correct_wheel_forces(wheels,service,other,parking,direction,override)
        for i,wheel in enumerate(expected):
            for offset,value in ((0x7c,wheel.spin_value),(0x88,wheel.spin_adjustment)):
                position=0x5fc+i*0x10c+offset
                observed=struct.unpack_from('<f',actual,position)[0]
                error=abs(value-observed)
                if error>max(.00005,abs(observed)*3e-7):
                    raise AssertionError((count,i,offset,value,observed))
                maximum=max(maximum,error)
                image[position:position+4]=actual[position:position+4]
        if actual != image:
            raise AssertionError('unexpected owner-state mutation')
        count+=1
    return {'cases':count,'maximum_absolute_error':maximum,
            'scope':'complete original 0x53e130; no substituted helpers; synthetic observed state'}


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('executable')
    print(json.dumps(verify(p.parse_args().executable)))
