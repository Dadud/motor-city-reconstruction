"""Bounded original mass/inertia/lever producers, before full startup."""
import argparse
import itertools
import json
import struct

from client.owner_binding import bind_owner_inertia,bind_axle_levers,bind_startup_com
from tools.native_oracle import DynoOracle


def verify(executable):
    o=DynoOracle(executable);cpu=o.cpu;reg=o.reg;owner=o.inputs;config=owner+0x3000
    count=0
    for mass,extents,shape in itertools.product((0.,575.,998.125,1800.25),
            ((.7,.6,1.8),(.7112,.5334,1.346),(.1234567,1.234567,3.456789)),range(-1,9)):
        o._reset();cpu.mem_write(owner,bytes(0x2000));cpu.reg_write(reg.UC_X86_REG_EBX,owner)
        cpu.mem_write(o.frame+0x10,struct.pack('<f',mass))
        o._run(0x51f4dd,0x51f518,count=1000)
        cpu.reg_write(reg.UC_X86_REG_EDI,owner);cpu.reg_write(reg.UC_X86_REG_ESI,config)
        cpu.mem_write(owner+0xcc,struct.pack('<3f',*extents));cpu.mem_write(config+0x48,struct.pack('<i',shape))
        cpu.mem_write(o.frame-0x20,struct.pack('<f',2.692))
        cpu.reg_write(reg.UC_X86_REG_EAX,o.frame-0x30)
        o._run(0x53a3f5,0x53a4be,count=5000)
        result=bind_owner_inertia(mass,extents,shape)
        actual=bytes(cpu.mem_read(owner+0x50,8))
        expected=struct.pack('<2f',result.mass,result.inverse_mass)
        if actual!=expected:raise AssertionError(('mass',count,actual.hex(),expected.hex()))
        actual=bytes(cpu.mem_read(o.frame-0x3f0,24))
        expected=struct.pack('<6f',*result.inertia,*result.inverse_inertia)
        if actual!=expected:raise AssertionError(('inertia',count,actual.hex(),expected.hex()))
        count+=1
    lever_count=0
    for wheelbase,fraction in itertools.product((.5,2.692,4.1234567),(-.1,0.,.4305,.5,1.,1.1)):
        o._reset();cpu.reg_write(reg.UC_X86_REG_EDI,owner)
        cpu.mem_write(owner+0x1c94,struct.pack('<I',config));cpu.mem_write(config+0x3c,struct.pack('<f',fraction))
        cpu.mem_write(o.frame-0x20,struct.pack('<f',wheelbase))
        o._run(0x53a7b6,0x53a7df,count=500)
        actual=bytes(cpu.mem_read(o.frame-0x40c,8));r=bind_axle_levers(wheelbase,fraction)
        if actual!=struct.pack('<2f',r.front,r.rear):raise AssertionError(('levers',lever_count))
        lever_count+=1
    com_count=0
    for height,half,marker,lever in itertools.product((.5334,1.),(.5,.8),(-1.2,1.346),(.5,1.532)):
        o._reset();cpu.reg_write(reg.UC_X86_REG_EBX,owner);cpu.reg_write(reg.UC_X86_REG_ESI,config)
        for offset,value in ((0xd0,half),(0x18c4,marker),(0x18b8,lever)):
            cpu.mem_write(owner+offset,struct.pack('<f',value))
        cpu.mem_write(config+0x38,struct.pack('<f',height))
        o._run(0x43ac8e,0x43acb1,count=500)
        result=bind_startup_com(height,half,marker,lever)
        if bytes(cpu.mem_read(owner+0x60,8))!=struct.pack('<2f',result.vertical,result.longitudinal):
            raise AssertionError(('startup_com',com_count))
        com_count+=1
    return {'inertia_and_mass_cases':count,'lever_cases':lever_count,'startup_com_cases':com_count,'maximum_absolute_error':0,
            'scope':'original 0x51f4dd mass binding; 0x53a3f5 inertia with actual shape helper; 0x53a7b6 levers; supplied finalized config/model observations; no complete assembled stock car claimed'}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('executable')
    print(json.dumps(verify(p.parse_args().executable)))
