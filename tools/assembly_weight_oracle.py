"""Compare the complete original weight-distribution helper without host calls."""
import argparse
import itertools
import json
import random
import struct

from client.assembly_weight import (FRONT_MASS_OFFSETS,REAR_MASS_OFFSETS,
    assembled_front_weight_fraction,finalize_weight_distribution)
from tools.native_oracle import DynoOracle


def cases():
    for body,fraction,length,shared in itertools.product((.125,575.,1200.25),
            (0.,.1,.4305,.5,.9,1.),(.125,2.6924,13.),(0.,37.125)):
        yield body,fraction,length,shared,(0.,)*23,(0.,)*13
    # Isolate every slot, including doubled and shared masses.
    for group,size in ((0,23),(1,13)):
        for index in range(size):
            for mass in (.125,27.3,1700.125):
                front=[0.]*23;rear=[0.]*13
                (front if group==0 else rear)[index]=mass
                yield 575.,.4305,2.6924,19.,front,rear
    rng=random.Random(539590)
    for _ in range(512):
        yield (rng.uniform(0,1500),rng.random(),rng.uniform(.01,20),
            rng.uniform(0,500),[rng.uniform(0,500) for _ in range(23)],
            [rng.uniform(0,500) for _ in range(13)])


def configuration(args):
    body,fraction,length,shared,front,rear=args
    image=bytearray(b'\xa5'*0x820)
    fields=((0x1c,body),(0x40,fraction),(0x2c,length),(0x680,shared),
        *zip(FRONT_MASS_OFFSETS,front),*zip(REAR_MASS_OFFSETS,rear))
    for offset,value in fields:struct.pack_into('<f',image,offset,value)
    return bytes(image)


def verify(executable):
    o=DynoOracle(executable);cpu=o.cpu;count=0
    # Private authored call wrapper stores both helper return and caller float.
    output=o.inputs+0x1000
    call_end=o.stub+10
    code=b'\x68'+struct.pack('<I',o.inputs)
    code+=b'\xe8'+struct.pack('<i',0x53b590-call_end)
    code+=b'\xdd\x15'+struct.pack('<I',output) # FST double, retain ST0
    code+=b'\xd9\x1d'+struct.pack('<I',output+8) # FSTP float
    code+=b'\x83\xc4\x04\xc3'
    cpu.mem_write(o.stub,code)
    for args in cases():
        o._reset();image=configuration(args)
        cpu.mem_write(o.inputs,image)
        stack=cpu.reg_read(o.reg.UC_X86_REG_ESP)
        cpu.mem_write(stack,struct.pack('<I',o.stop))
        o._run(o.stub,o.stop,count=1000)
        expected=assembled_front_weight_fraction(*args)
        actual=bytes(cpu.mem_read(output,12))
        if actual!=struct.pack('<df',expected,expected):
            raise AssertionError((count,struct.unpack('<df',actual),expected))
        if bytes(cpu.mem_read(o.inputs,0x820))!=image:
            raise AssertionError('helper changed configuration')
        final=finalize_weight_distribution(image,components_loaded=True)
        expected_image=bytearray(image);expected_image[0x3c:0x40]=actual[8:12]
        if final!=expected_image:raise AssertionError('final fraction store differs')
        count+=1
    return dict(cases=count,maximum_absolute_error=0,
        scope='complete original 0x53b590; exact double return and caller float store; unchanged input; supplied component slots, not complete assembly')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('executable')
    print(json.dumps(verify(p.parse_args().executable)))
