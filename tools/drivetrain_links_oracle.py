"""Bounded original condition/thermal routines with supplied damage/effect children."""
import argparse
from dataclasses import replace
import itertools
import json
import math
import struct
from client.drivetrain_links import *
from tools.native_oracle import DynoOracle

STATE={0xa44:'speed',0xabc:'normalized_rpm',0xac8:'engagement',0xacc:'auxiliary_temperature',0xad0:'auxiliary_capacity',0xad4:'condition',0xadc:'main_temperature',0xae0:'loss',0xb00:'drive_scale',0xb04:'primary_drive',0xb08:'alternate_drive',0xb58:'third_temperature',0xce0:'gate_one',0xce4:'gate_two',0xce8:'threshold_observation',0xcf0:'request',0xcf4:'rate_two',0xcf8:'rate_one',0xd54:'shielding_one',0xd58:'shielding_two'}
CONFIG={0x3e0:'alternate_threshold',0x448:'thermal_gain',0x4dc:'cooling_capacity',0x4e4:'main_loss_coefficient',0x4e8:'transfer_coefficient',0x4ec:'reference',0x6f0:'upgrade_enabled',0x6f8:'upgrade_cooling',0x6fc:'upgrade_capacity'}
CONFIG_INT={0x42c:'durability_index',0x4d8:'loss_index',0x4f4:'material_index'}

def cases():
    c=DrivetrainLinksConfig()
    for enabled,gate,temp,request,rate in itertools.product((0,1),(-.2,.7999999,.8,1.2),(-200.,200.,200.001,400.),(.05,.050001,.2),(-1000.,0.,1000.)):
        yield 'gear',DrivetrainLinksState(engine_flags=enabled,gate_one=gate,auxiliary_temperature=temp,request=request,rate_one=rate),c,{}
    for main,aux,condition,engagement,gate,speed,mode in itertools.product((89.999,90.,90.001,300.),(120.,120.001),(.5,1.1),(0.,.5),(.1,1.),(-30.,0.,30.),(0,1,2)):
        yield 'loads',DrivetrainLinksState(main_temperature=main,auxiliary_temperature=aux,condition=condition,engagement=engagement,gate_two=gate,speed=speed,mode=mode),c,{}
    for third,shield,upgrade,enabled,alternate,flags in itertools.product((129.999,130.,185.,200.),(-.5,.8,1.1),(0.,1.),(False,True),(False,True),(0,0x200)):
        yield 'loads',DrivetrainLinksState(third_temperature=third,shielding_one=shield,alternate_enabled=alternate,vehicle_flags=flags),replace(c,third_enabled=enabled,upgrade_enabled=upgrade,upgrade_cooling=.01,upgrade_capacity=3.),{}
    for condition in (.1,.9,1.1):yield 'loads',DrivetrainLinksState(bypass=True,condition=condition),c,{}
    for material,durability,loss_index,alternate_observation in itertools.product((0,4,100),(0,3),(-1,5),(.999999,1.,1.000001)):
        config=replace(c,material_index=material,durability_index=durability,loss_index=loss_index,
                       reference=75.25,cooling_capacity=4.75,transfer_coefficient=.023,thermal_gain=.017)
        state=DrivetrainLinksState(alternate_enabled=True,threshold_observation=alternate_observation,
                                  main_temperature=280.,auxiliary_temperature=200.001,condition=.333,
                                  rpm=8123,drive_scale=.734,normalized_rpm=.8723,rate_two=-.0001)
        yield 'loads',state,config,{}
        yield 'gear',replace(state,rate_one=123.456),config,{}

def mutation_cases():
    c=DrivetrainLinksConfig()
    for kind,code,name,value in (('gear',4,'request',.2),('gear',5,'engagement',.25),('loads',15,'third_temperature',150.),('loads',3,'condition',.5),('loads',3,'main_temperature',400.)):
        s=DrivetrainLinksState(gate_one=.9 if kind=='gear' else .1,request=.2,third_temperature=180.,main_temperature=300.,condition=1.1)
        yield kind,s,c,{code:((name,value),)}

class SuppliedLinkEffects:
    def __init__(self,mutations):self.mutations=mutations
    def __call__(self,action,state):
        if action.stage=='damage':
            for name,value in self.mutations.get(action.code,()):setattr(state,name,value)

def encode(s,c,config):
    image=bytearray([0xa5])*0x1d00;data=bytearray([0x5a])*0x800
    for off,name in STATE.items():struct.pack_into('<f',image,off,getattr(s,name))
    for off,value in ((0xae4,s.engine_flags),(0x474,s.vehicle_flags),(0xab4,s.rpm),(0x1c94,config)):struct.pack_into('<I',image,off,value&0xffffffff)
    image[0xa69]=s.mode;image[0xa86]=s.alternate_enabled
    for off,name in CONFIG.items():struct.pack_into('<f',data,off,getattr(c,name))
    for off,name in CONFIG_INT.items():struct.pack_into('<i',data,off,getattr(c,name))
    struct.pack_into('<i',data,0x68c,c.third_enabled)
    for i,v in enumerate(c.mode_coefficients):struct.pack_into('<f',data,0x354+i*4,v)
    return image,data

def verify(executable):
    from unicorn import UC_HOOK_CODE
    o=DynoOracle(executable);cpu,reg=o.cpu,o.reg;owner=o.inputs;config=owner+0x3000
    cpu.mem_write(0x5452c0,b'\xc3');cpu.mem_write(0x591180,b'\xc2\x08\x00');cpu.mem_write(0x591500,b'\xd9\xee\xc2\x14\x00')
    calls=[];mutations={}
    def child(cpu,address,size,user):
        stack=cpu.reg_read(reg.UC_X86_REG_ESP)
        if address==0x5452c0:
            receiver,code,value=struct.unpack('<IIf',cpu.mem_read(stack+4,12))
            if receiver!=owner:raise AssertionError('damage receiver')
            action=LinkCall('damage',code,(value,))
            for name,value in mutations.get(code,()):
                offset=next(off for off,n in STATE.items() if n==name);cpu.mem_write(owner+offset,struct.pack('<f',value))
        else:
            if cpu.reg_read(reg.UC_X86_REG_ECX)!=owner+0xcc8:raise AssertionError('effect receiver')
            n=4 if address==0x591500 else 1
            code=struct.unpack('<I',cpu.mem_read(stack+4,4))[0];values=struct.unpack('<'+'f'*n,cpu.mem_read(stack+8,4*n))
            action=LinkCall('effect_range' if n==4 else 'effect',code,values)
        calls.append(action)
    for address in (0x5452c0,0x591180,0x591500):cpu.hook_add(UC_HOOK_CODE,child,begin=address,end=address)
    count=0;maximum=0.
    for kind,s,c,mutations in itertools.chain(cases(),mutation_cases()):
        o._reset();before,data=encode(s,c,config);cpu.mem_write(owner,bytes(before));cpu.mem_write(config,bytes(data));cpu.mem_write(0x9aaa64,struct.pack('<I',s.bypass))
        calls.clear();stack=o.frame-0x1000;cpu.mem_write(stack,struct.pack('<II',o.stop,owner));cpu.reg_write(reg.UC_X86_REG_ESP,stack)
        o._run(0x546330 if kind=='gear' else 0x5464c0,o.stop,count=10000)
        output=(update_gear_link if kind=='gear' else update_drivetrain_loads)(s,c,SuppliedLinkEffects(mutations));expected,_=encode(output.state,c,config)
        if len(calls)!=len(output.calls):raise AssertionError((count,kind,'calls',calls,output.calls,s,c))
        for a,b in zip(calls,output.calls):
            if a.stage!=b.stage or a.code!=b.code or len(a.values)!=len(b.values) or any(abs(x-y)>max(.000002,abs(x)*3e-7) for x,y in zip(a.values,b.values)):raise AssertionError((count,'call',a,b))
        actual=bytes(cpu.mem_read(owner,len(before)))
        for off,name in STATE.items():
            a=struct.unpack_from('<f',actual,off)[0];b=struct.unpack_from('<f',expected,off)[0];error=abs(a-b)
            if not math.isfinite(a) or error>max(.00003,abs(a)*4e-7):raise AssertionError((count,kind,name,a,b,s,c))
            maximum=max(maximum,error);expected[off:off+4]=actual[off:off+4]
        if actual!=expected:raise AssertionError((count,'unexpected owner write'))
        if bytes(cpu.mem_read(config,len(data)))!=data:raise AssertionError('configuration write')
        count+=1
    return {'cases':count,'maximum_absolute_error':maximum,'scope':'complete condition and thermal routine bodies; supplied damage/effect children; exact call order and remaining owner/config bytes'}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('executable');print(json.dumps(verify(p.parse_args().executable)))
