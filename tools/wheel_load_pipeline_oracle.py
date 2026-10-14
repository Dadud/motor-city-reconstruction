"""Compare three recovered load stages on a shared original owner image.

Intervening driving helpers are excluded. Inputs are explicit synthetic state,
not a complete original tick or runtime scheduler.
"""
import argparse
import itertools
import json
import struct
from dataclasses import replace
from client.normal_load import NormalLoadInput, normal_load
from client.load_transfer import LoadTransferInput, transfer_load
from client.suspension_load_correction import SuspensionLoadInput, correct_suspension_load
from tools.native_oracle import DynoOracle


def verify(executable):
    o=DynoOracle(executable)
    cpu,reg=o.cpu,o.reg
    owner,config=o.inputs,o.inputs+0x3000
    force_offsets=(0x6cc,0x7d8,0x9f0,0x8e4)
    count,maximum=0,0.0
    for mask,pitch,bank,speed,longitudinal,lateral in itertools.product(range(16),
            (0,0.25,0.25001),(-0.1,0,0.1),(0,6,20),(-10,10),(-5,5)):
        support=tuple(bool(mask & (1<<i)) for i in range(4))
        initial=NormalLoadInput(support,pitch,bank,1450,2.7,1.6,1.7,0.55,
            1.2,1.5,speed,40,0,(9.8,10,9.5,9.9))
        transfer=LoadTransferInput((0,)*4,pitch,longitudinal,lateral,speed,
            1450,2.7,1.6,1.7,0.55,0.12,0.18)
        correction=SuspensionLoadInput((0,)*4,support,pitch,True,speed,bank,-0.06,
            1450,100,0.45,0.55,1.2,1.5,2.7,1.7,-2.3,500,0,False)
        image=bytearray([0xa5])*0x1d00
        struct.pack_into('<I',image,0x1c94,config)
        struct.pack_into('<I',image,0xc08,1)
        struct.pack_into('<I',image,0x474,0)
        image[0xa69]=3
        values=((0xc00,pitch),(0xc04,bank),(0x18b8,1.2),(0x18bc,1.5),
                (0xa2c,speed),(0xbe8,40),(0xa34,0),(0xa38,longitudinal),(0xa30,lateral),
                (0x18ec,0.12),(0x18f0,0.18),(0xbf8,bank),(0xbf4,-0.06),(0xaa0,500))
        for offset,value in values:
            struct.pack_into('<f',image,offset,value)
        for force,flag,scale,supported,value in zip(force_offsets,(0x6e8,0x7f4,0xa0c,0x900),
                (0x670,0x77c,0x994,0x888),support,initial.wheel_scales):
            image[flag]=int(supported)
            struct.pack_into('<f',image,scale,value)
            struct.pack_into('<3f',image,force,111,222,333)
        cpu.mem_write(owner,bytes(image))
        configuration=bytearray([0x5a])*0x700
        struct.pack_into('<i',configuration,0x6ec,0)
        for offset,value in ((0x20,1450),(0x28,100),(0x2c,2.7),(0x30,1.6),
                (0x34,1.7),(0x38,0.55),(0x104,0.45),(0xfc,0.55),(0x340,-2.3)):
            struct.pack_into('<f',configuration,offset,value)
        cpu.mem_write(config,bytes(configuration))
        loads=normal_load(initial)
        stages=((0x53d920,loads),)
        loads=transfer_load(replace(transfer,loads=loads))
        stages+=((0x53e680,loads),)
        loads=correct_suspension_load(replace(correction,loads=loads))
        stages+=((0x53e980,loads),)
        for entry,expected in stages:
            # Reset the bounded function-call CPU context, preserving owner/config.
            # This does not claim preservation of a full caller's x87 environment.
            o._reset()
            stack=o.frame-0x1000
            cpu.mem_write(stack,struct.pack('<II',o.stop,owner))
            cpu.reg_write(reg.UC_X86_REG_ESP,stack)
            o._run(entry,o.stop,count=20000)
            actual=bytes(cpu.mem_read(owner,len(image)))
            for force,target in zip(force_offsets,expected):
                x,value,z=struct.unpack_from('<3f',actual,force)
                error=abs(value-target)
                if x!=0 or z!=0 or error>max(0.00025,abs(value)*3e-7):
                    raise AssertionError((count,hex(entry),hex(force),value,target,error))
                maximum=max(maximum,error)
                struct.pack_into('<3f',image,force,x,value,z)
            if actual!=image or cpu.mem_read(config,len(configuration))!=configuration:
                raise AssertionError('unexpected composed owner/configuration mutation')
        count+=1
    return {'scenarios':count,'stage_comparisons':count*3,'maximum_absolute_error':maximum,
        'scope':'shared owner across 0x53d920 -> 0x53e680 -> 0x53e980; original trig; no substitutions; intervening helpers/scheduler excluded; per-call CPU reset'}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    print(json.dumps(verify(parser.parse_args().executable)))
