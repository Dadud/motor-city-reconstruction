"""Full original 0x540520 using actual original turn sine/cosine."""
import argparse
import itertools
import json
import math
import struct
from client.wheel_force_orientation import ForceOrientationWheel, orient_wheel_forces
from tools.native_oracle import DynoOracle


def cases():
    for angle,phase,front,rear,force in itertools.product(
            (-.2,0,.2),(-.125,0,.125),(-2,0,2),(-3,0,3),(-1000,0,1000)):
        yield tuple(ForceOrientationWheel(angle*(i-1),phase,force+i*31,force-i*57) for i in range(4)),front,rear


def verify(executable):
    o=DynoOracle(executable)
    cpu,reg=o.cpu,o.reg
    count,maximum=0,0.0
    for wheels,front,rear in cases():
        o._reset()
        image=bytearray([0xa5])*0x1d00
        for off,val in ((0xd08,front),(0xd0c,rear)):
            struct.pack_into('<f',image,off,val)
        for i,w in enumerate(wheels):
            for off,val in ((0,w.steering_angle),(0xf4,w.phase_angle),(0xd0,w.lateral_force),(0xd8,w.longitudinal_force)):
                struct.pack_into('<f',image,0x5fc+i*0x10c+off,val)
        cpu.mem_write(o.inputs,bytes(image))
        stack=o.frame-0x1000
        cpu.mem_write(stack,struct.pack('<II',o.stop,o.inputs))
        cpu.reg_write(reg.UC_X86_REG_ESP,stack)
        o._run(0x540520,o.stop,count=20000)
        actual=bytes(cpu.mem_read(o.inputs,len(image)))
        for i,w in enumerate(orient_wheel_forces(wheels,front,rear)):
            for off,target in ((0xd0,w.lateral_force),(0xd8,w.longitudinal_force)):
                offset=0x5fc+i*0x10c+off
                value=struct.unpack_from('<f',actual,offset)[0]
                error=abs(value-target)
                if not math.isfinite(value) or error>max(.00025,abs(value)*3e-7):
                    raise AssertionError((count,i,off,value,target,error))
                maximum=max(maximum,error)
                image[offset:offset+4]=actual[offset:offset+4]
        if actual!=image:
            raise AssertionError('unexpected owner writes')
        count+=1
    return {'cases':count,'maximum_absolute_error':maximum,'scope':'complete 0x540520; actual original trigonometric helpers; all other owner bytes unchanged'}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('executable')
    print(json.dumps(verify(p.parse_args().executable)))
