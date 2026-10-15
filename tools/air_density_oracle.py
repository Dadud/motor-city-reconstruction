"""Complete original air-density calculation plus actual weather/floor helpers."""
import argparse
import itertools
import json
import struct
from client.air_density import calculate_air_density
from tools.native_oracle import DynoOracle


def cases():
    altitudes=(-500,-499.99,-.01,0,.01,499.99,500,500.01,1000,2000,3500,4500,5499)
    yield from itertools.product(altitudes,(False,True),(False,True),(0,1,2,3,0xffffffff))


def verify(executable):
    o=DynoOracle(executable);cpu,reg=o.cpu,o.reg
    owner,out=o.inputs,o.inputs+0x3000
    code=b'\x68'+struct.pack('<I',owner)
    code+=b'\xe8'+struct.pack('<i',0x535ed0-(o.stub+len(code)+5))
    code+=b'\x83\xc4\x04\xd9\x1d'+struct.pack('<I',out)+b'\xc3'
    cpu.mem_write(o.stub,code)
    count=0
    for altitude,cold,enabled,weather in cases():
        o._reset();image=bytearray([0xa5])*0x1d00
        struct.pack_into('<f',image,0x34c,altitude);cpu.mem_write(owner,bytes(image))
        for address,value in ((0x9aaa5c,int(cold)),(0x9aaa60,int(enabled)),(0xb12958,weather)):
            cpu.mem_write(address,struct.pack('<I',value))
        stack=o.frame-0x1000;cpu.mem_write(stack,struct.pack('<I',o.stop));cpu.reg_write(reg.UC_X86_REG_ESP,stack)
        o._run(o.stub,o.stop,count=50000)
        actual=struct.unpack('<f',cpu.mem_read(out,4))[0]
        expected=calculate_air_density(altitude,cold,enabled,weather)
        if actual!=expected: raise AssertionError((count,actual,expected,altitude,cold,enabled,weather))
        if bytes(cpu.mem_read(owner,len(image)))!=image: raise AssertionError('unexpected owner writes')
        count+=1
    return {'cases':count,'maximum_absolute_error':0,'scope':'complete535ed0,594030,69a630; no substitutions; float32 consumer handoff'}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('executable')
    print(json.dumps(verify(p.parse_args().executable)))
