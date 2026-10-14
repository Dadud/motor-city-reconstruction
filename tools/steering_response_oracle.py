"""Complete original steering-shaping helper, synthetic input state."""
import argparse
import itertools
import json
import struct
from client.steering_response import steering_response
from tools.native_oracle import DynoOracle


def cases():
    for raw,speed in itertools.product((*range(-128,128),-0x80000000,0x7fffffff),
            (-100,-44.704,-44.703,0,10,44.703,44.704,100)):
        yield raw,speed


def verify(executable):
    o=DynoOracle(executable)
    cpu,reg=o.cpu,o.reg
    owner=o.inputs
    cpu.mem_write(o.stub,b'\xdd\x1d'+struct.pack('<I',o.inputs+0x4000))
    count,maximum=0,0.0
    for raw,speed in cases():
        o._reset()
        image=bytearray([0xa5])*0x1d00
        struct.pack_into('<i',image,0xa7c,raw)
        struct.pack_into('<f',image,0xa44,speed)
        cpu.mem_write(owner,bytes(image))
        stack=o.frame-0x1000
        cpu.mem_write(stack,struct.pack('<II',o.stop,owner))
        cpu.reg_write(reg.UC_X86_REG_ESP,stack)
        o._run(0x541930,o.stop,count=20000)
        o._run(o.stub,o.stub+6,count=1)
        actual=struct.unpack('<d',cpu.mem_read(o.inputs+0x4000,8))[0]
        expected=steering_response(raw,speed)
        error=abs(actual-expected)
        if error>1e-7 or cpu.mem_read(owner,len(image))!=image:
            raise AssertionError((raw,speed,actual,expected,error))
        maximum=max(maximum,error)
        count+=1
    return {'cases':count,'maximum_absolute_error':maximum,
            'scope':'complete 0x541930; no substituted calls; signed control and speed observations; full owner unchanged'}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('executable')
    print(json.dumps(verify(p.parse_args().executable)))
