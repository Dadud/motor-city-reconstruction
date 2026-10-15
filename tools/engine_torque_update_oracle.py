"""Full original torque update with real power, environment and RPM helpers."""
import argparse
from dataclasses import replace
import itertools
import json
import math
import struct
from client.engine_torque_update import *
from tools.driving_engine_rpm_oracle import FIELDS,INTS as RPM_INTS
from tools.native_oracle import DynoOracle

STATE={0xaa0:'curve_torque',0xaa4:'effective_torque',0xaac:'power',0xb2c:'engagement',0xa90:'brake_control',0xcec:'condition_accumulator',0xd50:'condition_gate',0xd3c:'damage_d3c',0xd40:'damage_d40',0xd44:'damage_d44',0xd48:'damage_d48',0xd4c:'damage_d4c',0xae0:'loss',0xacc:'auxiliary_temperature',0xce8:'boost_observation',0xa2c:'effect_motion',0xb24:'drag_factor',0xb6c:'drag_speed',0xb70:'drag',0xb3c:'coupling_resistance',0x34c:'environment_field'}
CONFIG={0x6f0:'upgrade_enabled',0x3e0:'boost_threshold',0x3e4:'boost_available',0x378:'exhaust_tag',0x54:'compression',0x4b8:'overload_coefficient',0x688:'torque_capacity'}
CONFIG_INTEGERS={0x4d8:'loss_index',0x4f4:'material_index',0x6f4:'upgrade_index',0x3c8:'gain_mode',0x42c:'durability_index',0x4a8:'limit_a',0x4b0:'limit_b',0x508:'overspeed_base',0x570:'overspeed_extra',0x43c:'overload_index'}

def base():
    r=DrivingEngineRPM(600,9000,.7,.4,4000,True,.7,100.,3000*f32(.10471976),3000,8500,2,175.5,20.)
    return EngineTorqueState(r,drag_factor=.12,drag_speed=20.,effect_motion=-42.),EngineTorqueConfig(tuple(100.+i*13.5 for i in range(22)))

def cases():
    s,c=base()
    for rpm,throttle,enabled,engagement,bypass in itertools.product((0,599,600,3000,8000),(0.,.3,.300001,.8,.800001,1.),(0,1),(0.,.5,1.),(False,True)):
        yield replace(s,rpm_state=replace(s.rpm_state,rpm=rpm,throttle=throttle,angular_speed=f32(rpm*f32(.10471976))),engine_flags=enabled,engagement=engagement,bypass=bypass),c,{'brake_query':1,'pulse':.625,'rpm_limit':7000,'boost':(17.5,.25)}
    for field,value,load,response in itertools.product(('damage_d3c','damage_d40','damage_d44','damage_d48','damage_d4c','condition_accumulator'),(.249999,.25,.75,1.),(.349999,.35,.350001,.6,.600001),(-.1,.5,1.5)):
        r=replace(s.rpm_state,throttle=1.,rpm=round(load*8500))
        state=replace(s,rpm_state=r,condition_gate=1.);setattr(state,field,value)
        yield state,c,{'pulse':response,'rpm_limit':10000}
    for alternate,observation,exhaust,available,rpm in itertools.product((False,True),(.999999,1.),(0.,1.),(0.,1.),(3000,8500)):
        yield replace(s,rpm_state=replace(s.rpm_state,rpm=rpm),alternate_enabled=alternate,boost_observation=observation),replace(c,exhaust_tag=exhaust,boost_available=available,compression=10.),{'boost':(17.5,.25),'rpm_limit':6500}
    for gain,third,upgrade,temp,query in itertools.product(range(6),(False,True),(0.,1.),(120.,120.001),(0,1,256)):
        yield replace(s,rpm_state=replace(s.rpm_state,throttle=.9),auxiliary_temperature=temp),replace(c,gain_mode=gain,third_enabled=third,upgrade_enabled=upgrade,torque_capacity=100.,overload_index=1),{'rpm_limit':2500}
        yield replace(s,rpm_state=replace(s.rpm_state,throttle=0.),brake_control=.3),replace(c,third_enabled=third),{'brake_query':query,'rpm_limit':10000}
    for gain,throttle in itertools.product((0,2,3,4,5),(.299999,.3,.300001,.799999,.8,.800001)):
        yield replace(s,rpm_state=replace(s.rpm_state,throttle=throttle)),replace(c,gain_mode=gain),{'rpm_limit':10000}
    for rpm,environment,capacity in itertools.product((6500,6501,8000),((False,False,0,-100000.),(False,True,2,1250.),(True,True,1,100000.)),(50.,1000.)):
        override,selector_enabled,selector,field=environment
        yield replace(s,rpm_state=replace(s.rpm_state,rpm=rpm,throttle=.9,angular_speed=f32(rpm*f32(.10471976))),environment_override=override,environment_selector_enabled=selector_enabled,environment_selector=selector,environment_field=field),replace(c,durability_index=1,overspeed_base=1000,overspeed_extra=25,overload_index=1,torque_capacity=capacity),{'rpm_limit':2500}

def mutation_cases():
    s,c=base()
    for stage,name,value in (('pulse','loss',3.25),('pulse','rpm.throttle',.1),('brake_query','brake_control',.75),('boost','effective_torque',3.25),('rpm_limit','rpm.rpm',8000),('damage','curve_torque',999.5)):
        state=replace(s,damage_d40=.5,alternate_enabled=stage=='boost')
        if stage=='brake_query':state.rpm_state=replace(state.rpm_state,throttle=0.)
        yield state,replace(c,torque_capacity=100.),{'brake_query':1,'pulse':.5,'boost':(17.5,.25),'rpm_limit':2500,'mutations':{stage:((name,value),)}}

class SuppliedTorqueStages:
    def __init__(self,observations):self.observations=observations
    def __call__(self,action,state):
        for name,value in self.observations.get('mutations',{}).get(action.stage,()):
            if name.startswith('rpm.'):state.rpm_state=replace(state.rpm_state,**{name[4:]:value})
            else:setattr(state,name,value)
        if action.stage in ('damage','effect'):return None
        return self.observations.get(action.stage,(0.,0.) if action.stage=='boost' else 0)

def encode(s,c,config):
    image=bytearray([0xa5])*0x1d00;data=bytearray([0x5a])*0x800
    for name,off in FIELDS.items():struct.pack_into('<i' if name in RPM_INTS else '<f',image,off,getattr(s.rpm_state,name))
    for off,name in STATE.items():struct.pack_into('<f',image,off,getattr(s,name))
    for off,value in ((0xae4,s.engine_flags),(0x11c0,s.boost_flag),(0x1c94,config)):struct.pack_into('<I',image,off,value&0xffffffff)
    image[0xa86]=s.alternate_enabled
    struct.pack_into('<f',image,0x1810+s.rpm_state.gear_index*4,s.rpm_state.gear_speed_factor)
    struct.pack_into('<ii',data,0x6c,s.rpm_state.idle_rpm,s.rpm_state.configured_max_rpm)
    for off,name in CONFIG.items():struct.pack_into('<f',data,off,getattr(c,name))
    for off,name in CONFIG_INTEGERS.items():struct.pack_into('<i',data,off,getattr(c,name))
    struct.pack_into('<i',data,0x68c,c.third_enabled)
    for i,v in enumerate(c.torque_curve):struct.pack_into('<f',data,0x80+4*i,v)
    return image,data

def verify(executable):
    from unicorn import UC_HOOK_CODE
    o=DynoOracle(executable);cpu,reg=o.cpu,o.reg;owner=o.inputs;config=owner+0x3000;result=owner+0x4000
    # Supplied x87-return children read a private double slot; their code/data is
    # confined to emulated memory. Original math/environment/RPM run unchanged.
    for address in (0x4b7170,0x549580):cpu.mem_write(address,b'\xdd\x05'+struct.pack('<I',result)+b'\xc3')
    for address,code in ((0x5452c0,b'\xc3'),(0x591180,b'\xc2\x08\x00'),(0x55cfc0,b'\xc3'),(0x54d250,b'\xc3')):cpu.mem_write(address,code)
    addresses={0x4b7170:'pulse',0x549580:'boost',0x5452c0:'damage',0x591180:'effect',0x55cfc0:'brake_query',0x54d250:'rpm_limit',0x535e20:'environment',0x546e70:'rpm_update'}
    calls=[];observations={}
    def child(cpu,address,size,user):
        stack=cpu.reg_read(reg.UC_X86_REG_ESP);stage=addresses[address];code=None;values=()
        if stage=='pulse':values=struct.unpack('<4f',cpu.mem_read(stack+4,16))
        elif stage=='rpm_limit':values=struct.unpack('<2i',cpu.mem_read(stack+4,8))
        elif stage=='effect':
            if cpu.reg_read(reg.UC_X86_REG_ECX)!=owner+0xcc8:raise AssertionError('effect receiver')
            code,value=struct.unpack('<If',cpu.mem_read(stack+4,8));values=(value,)
        else:
            receiver=struct.unpack('<I',cpu.mem_read(stack+4,4))[0]
            if receiver!=owner:raise AssertionError((stage,'owner receiver'))
            if stage=='damage':code,value=struct.unpack('<If',cpu.mem_read(stack+8,8));values=(value,)
            elif stage=='rpm_update':code=struct.unpack('<i',cpu.mem_read(stack+8,4))[0]
        calls.append(TorqueCall(stage,code,values))
        if stage in ('environment','rpm_update'):return
        for name,value in observations.get('mutations',{}).get(stage,()):
            if name.startswith('rpm.'):
                name=name[4:];off=FIELDS[name];fmt='i' if name in RPM_INTS else 'f'
            else:off=next(off for off,n in STATE.items() if n==name);fmt='f'
            cpu.mem_write(owner+off,struct.pack('<'+fmt,value))
        value=observations.get(stage,(0.,0.) if stage=='boost' else 0)
        if stage=='boost':
            value,increment=value;pointer=struct.unpack('<I',cpu.mem_read(stack+8,4))[0];cpu.mem_write(pointer,struct.pack('<f',increment))
        if stage in ('boost','pulse'):cpu.mem_write(result,struct.pack('<d',float(value)))
        elif stage in ('rpm_limit','brake_query'):cpu.reg_write(reg.UC_X86_REG_EAX,int(value)&0xffffffff)
    for address in addresses:cpu.hook_add(UC_HOOK_CODE,child,begin=address,end=address)
    maximum=0.;count=0
    for s,c,observations in itertools.chain(cases(),mutation_cases()):
        o._reset();before,data=encode(s,c,config);cpu.mem_write(owner,bytes(before));cpu.mem_write(config,bytes(data));calls.clear()
        for address,value in ((0x9aaa64,s.bypass),(0xaa456c,s.counter),(0x9aaa5c,s.environment_override),(0x9aaa60,s.environment_selector_enabled),(0xb12958,s.environment_selector)):cpu.mem_write(address,struct.pack('<i',value))
        stack=o.frame-0x1000;cpu.mem_write(stack,struct.pack('<II',o.stop,owner));cpu.reg_write(reg.UC_X86_REG_ESP,stack)
        o._run(0x547120,o.stop,count=100000)
        output=update_engine_torque(s,c,SuppliedTorqueStages(observations));expected,_=encode(output.state,c,config)
        if len(calls)!=len(output.calls):raise AssertionError((count,'calls',calls,output.calls,s,c,observations))
        for a,b in zip(calls,output.calls):
            if a.stage!=b.stage or a.code!=b.code or len(a.values)!=len(b.values) or any(abs(x-y)>max(.000002,abs(x)*4e-7) for x,y in zip(a.values,b.values)):raise AssertionError((count,'call',a,b,s,c))
        actual=bytes(cpu.mem_read(owner,len(before)))
        for off in [off for name,off in FIELDS.items() if name not in RPM_INTS]+list(STATE):
            a=struct.unpack_from('<f',actual,off)[0];b=struct.unpack_from('<f',expected,off)[0];error=abs(a-b)
            if not math.isfinite(a) or error>max(.0001,abs(a)*4e-7):raise AssertionError((count,hex(off),a,b,s,c,observations))
            maximum=max(maximum,error);expected[off:off+4]=actual[off:off+4]
        if actual!=expected:
            off=next(i for i,(a,b) in enumerate(zip(actual,expected)) if a!=b);raise AssertionError((count,'owner bytes',hex(off),actual[off:off+4],expected[off:off+4],s,c,observations))
        if bytes(cpu.mem_read(config,len(data)))!=data:raise AssertionError('configuration write')
        count+=1
    return {'cases':count,'maximum_absolute_error':maximum,'scope':'complete torque body with original power, environment and RPM helpers; explicit supplied pulse/boost/query/limit/damage/effect producers'}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('executable');print(json.dumps(verify(p.parse_args().executable)))
