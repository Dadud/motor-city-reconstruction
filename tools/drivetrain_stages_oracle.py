"""Whole-owner original comparisons of five recovered drivetrain bodies."""
import argparse
from dataclasses import replace
import itertools
import json
import math
import struct
from client.drivetrain_stages import *
from tools.native_oracle import DynoOracle

FLOATS={0xa94:'throttle',0xb2c:'engagement',0xb30:'clutch_gain',0xab0:'angular_speed',
    0xb3c:'coupling_resistance',0xaa4:'effective_torque',0xb40:'transmitted_torque',
    0xb44:'reference_rotation',0xb48:'output_torque',0xb50:'driven_speed',0xb68:'previous_rotation',
    0xb6c:'drag_speed',0xb74:'prior_output_rotation',0xb78:'final_drive_acceleration',
    0xb7c:'gearbox_drag',0xb80:'output_rotation',0xb84:'wheel_acceleration',0xb88:'accumulated_drag',
    0x18b0:'inertia_sum',0xa44:'longitudinal_speed',0xa38:'acceleration',0xa2c:'speed',
    0x3b4:'alternate_speed',0xd5c:'damage_one',0xd60:'damage_two',0xcf0:'request'}
INTS={0xae4:'engine_flags',0x474:'vehicle_flags',0xab4:'rpm',0xb54:'gear',0xb64:'hold_ticks',0x404:'component_mode'}
BYTES={0xa88:'override_byte',0xa66:'raw_throttle',0xa89:'auxiliary_byte'}
WHEEL_FLOATS={0x7c:'spin',0x88:'adjustment',0xbc:'radius',0x94:'inertia',0xa0:'conversion',
    0xac:'distribution',0xb0:'torque',0xd4:'normal_load',0xd8:'longitudinal_force'}
CONFIG_FLOATS={0x374:'final_drive',0x6e0:'torque_capacity',0x6e8:'efficiency',0x3ec:'option_one',
    0x3f4:'option_two',0x388:'increment_gain',0x400:'secondary_gain'}
CONFIG_INTS={0x694:'clutch_steps',0x70:'maximum_rpm',0x68c:'third_enabled',0x3f0:'option_kind',0x3fc:'secondary_kind'}
ENTRIES={'clutch':0x545ec0,'prepare':0x546130,'request':0x546ad0,'distribute':0x547c60,'apply':0x548050}
METHODS={'clutch':update_clutch,'prepare':prepare_drive,'request':accumulate_drive_request,
    'distribute':distribute_drive,'apply':apply_drive_forces}


def base():
    s=DriveState(wheels=[DriveWheel(spin=(i-1)*8,radius=.25+i*.03,inertia=1+i*.1,
        conversion=.6+i*.1,distribution=.1+i*.05,torque=100+i*50,normal_load=2000+i*400,
        longitudinal_force=23-i*17,adjustment=2-i) for i in range(4)],driven_speed=20,
        longitudinal_speed=8,acceleration=.5,clutch_gain=.8,previous_rotation=100,
        prior_output_rotation=60,speed=8,alternate_speed=3,reference_rotation=50,
        output_torque=300,drag_speed=3,final_drive_acceleration=2,wheel_acceleration=1.5)
    c=DriveConfig((2.5,0,2.2,1.7,1.3,1.,.8,.7),(.8,1.,.7,.9,.8,.9,.9,.9),
        (.2,.4,.8,1.2,1.3,1.4,1.5,1.6),(.002,.003,.004,.005,.006,.007,.008,.009),
        3.5,500,.9,16,7000,False,0,0,0,0,0,0)
    return s,c


def encode(s,c,config,owner):
    image=bytearray(b'\xa5'*0x2000);data=bytearray(b'\x5a'*0x800)
    struct.pack_into('<I',image,0x1c94,config)
    for off,name in FLOATS.items():struct.pack_into('<f',image,off,getattr(s,name))
    for off,name in INTS.items():struct.pack_into('<I',image,off,getattr(s,name)&0xffffffff)
    for off,name in BYTES.items():image[off]=getattr(s,name)
    for i,w in enumerate(s.wheels):
        start=0x5fc+i*0x10c
        for off,name in WHEEL_FLOATS.items():struct.pack_into('<f',image,start+off,getattr(w,name))
        image[start+0xc5]=int(w.driven);image[start+0xec]=int(w.contact)
    for off,name in CONFIG_FLOATS.items():struct.pack_into('<f',data,off,getattr(c,name))
    for off,name in CONFIG_INTS.items():struct.pack_into('<i',data,off,int(getattr(c,name)))
    for off,values,target in ((0x334,c.gear_ratios,data),(0x354,c.gear_losses,data),
            (0x1870,c.inertia_factors,image),(0x1830,c.speed_factors,image)):
        struct.pack_into('<'+'f'*len(values),target,off,*values)
    return image,data


def cases():
    s,c=base()
    for engagement,third,override,throttle,speed,damage,resistance,bypass in itertools.product(
            (0.,.03,.5,.99,1.),(False,True),(0,1,2),(0.,.009999,.01,.5),(24.999,25.),(.49999,.5),(200.,200.001),(False,True)):
        yield 'clutch',replace(s,engagement=engagement,override_byte=override,throttle=throttle,
            driven_speed=speed,damage_one=damage,coupling_resistance=resistance,bypass=bypass),replace(c,third_enabled=third),True
    for gear,engagement,mask,acceleration in itertools.product((0,1,2,7),(0.,.5,1.),(0,1,5,15),(-200.,0.,200.)):
        yield 'prepare',replace(s,gear=gear,engagement=engagement,acceleration=acceleration,
            wheels=[replace(w,contact=bool(mask&(1<<i)),driven=i%2==0) for i,w in enumerate(s.wheels)]),c,True
    for mode,speed,kind,gain,secondary in itertools.product(range(9),(2.5,2.50001),(0,1,2,3),(0.,10.),(0.,.2)):
        yield 'request',replace(s,component_mode=mode,alternate_speed=speed,request=.99999),replace(c,
            option_one=1,option_two=1,option_kind=kind,increment_gain=gain,secondary_gain=secondary,secondary_kind=kind),True
    for gear,torque,engagement,hold,damage,bypass,mode in itertools.product((0,1,2),(-1.,0.,100.,1000.),(0.,1.),(0,1,-1),(.24999,.25,.75),(False,True),(0,0x10)):
        yield 'distribute',replace(s,gear=gear,effective_torque=torque,engagement=engagement,
            hold_ticks=hold,damage_one=damage,damage_two=.5,bypass=bypass,vehicle_flags=4|mode),c,True
    for gear,flags,mask,gate,velocity in itertools.product((0,1,2,7),(1,0x21),(0,5,15),(False,True),(-40.,0.,40.)):
        yield 'apply',replace(s,gear=gear,engine_flags=flags,longitudinal_speed=velocity,
            wheels=[replace(w,driven=bool(mask&(1<<i)),contact=i%2==0) for i,w in enumerate(s.wheels)]),c,gate


def verify(executable):
    from unicorn import UC_HOOK_CODE
    o=DynoOracle(executable);cpu,reg=o.cpu,o.reg;owner=o.inputs;config=owner+0x3000
    calls=[];gate=True
    effect_return=o.stub+0x400;cpu.mem_write(effect_return,b'\xc2\x08\x00')
    def hook(cpu,address,size,user):
        stack=cpu.reg_read(reg.UC_X86_REG_ESP);ret=struct.unpack('<I',cpu.mem_read(stack,4))[0]
        if address==0x55cfc0:
            if struct.unpack('<I',cpu.mem_read(stack+4,4))[0]!=owner:raise AssertionError('drive gate owner')
            calls.append(DriveCall('vehicle_gate'));cpu.reg_write(reg.UC_X86_REG_EAX,int(gate))
        elif address==0x5452c0:
            receiver,code,value=struct.unpack('<IIf',cpu.mem_read(stack+4,12))
            if receiver!=owner:raise AssertionError('drive damage owner')
            calls.append(DriveCall('damage',code,(value,)))
        else:
            code,value=struct.unpack('<If',cpu.mem_read(stack+4,8))
            if cpu.reg_read(reg.UC_X86_REG_ECX)!=owner+0xcc8:raise AssertionError('drive effect owner')
            calls.append(DriveCall('effect',code,(value,)));cpu.reg_write(reg.UC_X86_REG_EIP,effect_return);return
        cpu.reg_write(reg.UC_X86_REG_ESP,stack+4);cpu.reg_write(reg.UC_X86_REG_EIP,ret)
    for address in (0x55cfc0,0x5452c0,0x591180):cpu.hook_add(UC_HOOK_CODE,hook,begin=address,end=address)
    maximum=0.;counts={}
    for stage,s,c,gate in cases():
        before,data=encode(s,c,config,owner);cpu.mem_write(owner,bytes(before));cpu.mem_write(config,bytes(data))
        cpu.mem_write(0x9aaa64,struct.pack('<I',s.bypass));cpu.mem_write(0x9abb04,struct.pack('<I',s.mode_setting))
        cpu.mem_write(0x9aa9a0,struct.pack('<I',0));cpu.mem_write(0x98c1e8,struct.pack('<I',owner if s.local_player else owner+0x8000))
        o._reset();calls.clear();stack=o.frame-0x1000;cpu.mem_write(stack,struct.pack('<II',o.stop,owner));cpu.reg_write(reg.UC_X86_REG_ESP,stack)
        o._run(ENTRIES[stage],o.stop,count=100000)
        expected_calls=[]
        def execute(action,current):expected_calls.append(action);return gate if action.stage=='vehicle_gate' else None
        output=METHODS[stage](s,c,execute) if stage in ('distribute','apply') else METHODS[stage](s,c)
        expected,_=encode(output,c,config,owner);actual=bytes(cpu.mem_read(owner,len(before)))
        positions=set(FLOATS)|{0x5fc+i*0x10c+off for i in range(4) for off in WHEEL_FLOATS}
        for off in positions:
            a,b=struct.unpack_from('<f',actual,off)[0],struct.unpack_from('<f',expected,off)[0];error=abs(a-b)
            if not math.isfinite(a) or error>max(.0001,abs(a)*4e-7):raise AssertionError((stage,counts.get(stage,0),hex(off),a,b,error,s,c))
            maximum=max(maximum,error);expected[off:off+4]=actual[off:off+4]
        if actual!=expected or bytes(cpu.mem_read(config,len(data)))!=data:raise AssertionError((stage,'unexpected owner/configuration write'))
        if len(calls)!=len(expected_calls):raise AssertionError((stage,'call count',calls,expected_calls))
        for a,b in zip(calls,expected_calls):
            if (a.stage,a.code)!=(b.stage,b.code) or len(a.values)!=len(b.values) or any(not math.isclose(x,y,rel_tol=4e-7,abs_tol=1e-7) for x,y in zip(a.values,b.values)):
                raise AssertionError((stage,'call',a,b))
        counts[stage]=counts.get(stage,0)+1
    return dict(cases=counts,maximum_absolute_error=maximum,scope='five complete original drivetrain bodies; original mode selector; explicit damage/effects and vehicle gate; whole owner/configuration checked')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('executable');print(json.dumps(verify(p.parse_args().executable)))
