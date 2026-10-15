"""Original dispatcher with real connected torque/condition/RPM/math consumers."""
import argparse
from dataclasses import replace
import itertools
import json
import math
import struct
from client.engine_pipeline import *
from tools.engine_torque_update_oracle import encode as encode_torque,STATE as TORQUE_STATE,CONFIG as TORQUE_CONFIG,CONFIG_INTEGERS,base as torque_base
from tools.drivetrain_links_oracle import encode as encode_links,STATE as LINK_STATE,CONFIG as LINK_CONFIG,CONFIG_INT
from tools.driving_engine_rpm_oracle import FIELDS,INTS
from tools.engine_update_oracle import STAGES
from tools.native_oracle import DynoOracle

DISPATCH_FLOATS={0xe0c:'override_value',0x105c:'motion_metric'}
OWNER_FLOATS={**TORQUE_STATE,**LINK_STATE,**DISPATCH_FLOATS}
# These aliases deliberately distinguish the two engagement records.
OWNER_FLOATS[0xac8]='thermal_engagement'
OWNER_FLOATS[0xce8]='boost_observation'
OWNER_FLOATS[0xa44]='rpm.longitudinal_speed'
OWNER_FLOATS[0xabc]='rpm.normalized_rpm'
OWNER_INTS={0xae4:'engine_flags',0x474:'vehicle_flags',0x464:'selector_index',0x11c0:'boost_flag'}
OWNER_BYTES={0xa86:'alternate_enabled',0xa87:'control_gate',0xa69:'thermal_mode'}

def encode(s,c,config):
    from client.engine_pipeline import _torque,_links
    image,data=encode_torque(_torque(s),c.torque,config)
    links,link_data=encode_links(_links(s),c.links,config)
    for off in LINK_STATE:image[off:off+4]=links[off:off+4]
    for off in (0xae4,0x474,0xab4):image[off:off+4]=links[off:off+4]
    for off in (0xa69,0xa86):image[off]=links[off]
    for off in (*LINK_CONFIG,*CONFIG_INT,0x68c):data[off:off+4]=link_data[off:off+4]
    data[0x354:0x354+4*len(c.links.mode_coefficients)]=link_data[0x354:0x354+4*len(c.links.mode_coefficients)]
    for off,n in DISPATCH_FLOATS.items():struct.pack_into('<f',image,off,getattr(s,n))
    for off,n in OWNER_INTS.items():struct.pack_into('<I',image,off,getattr(s,n)&0xffffffff)
    image[0xa87]=int(s.control_gate)
    return image,data

def base():
    torque,config=torque_base()
    s=EnginePipelineState(**{f.name:getattr(torque,f.name) for f in fields(EngineTorqueState)})
    links=DrivetrainLinksConfig(material_index=config.material_index,durability_index=config.durability_index,
                               loss_index=config.loss_index,third_enabled=config.third_enabled,
                               upgrade_enabled=config.upgrade_enabled,alternate_threshold=config.boost_threshold)
    return s,EnginePipelineConfig(config,links)

def cases():
    s,c=base()
    for flags,enabled,throttle,engagement,thermal_engagement,third in itertools.product((0,2,3,4,6,7),(0,1),(0.,.7,1.),(0.,.5,1.),(.1,.9),(False,True)):
        state=replace(s,rpm_state=replace(s.rpm_state,throttle=throttle),vehicle_flags=flags,engine_flags=enabled,
                      engagement=engagement,thermal_engagement=thermal_engagement,condition_gate=.4)
        config=replace(c,torque=replace(c.torque,third_enabled=third),links=replace(c.links,third_enabled=third))
        observation={'query_8':0,'query_1':1,'start_counter':2000,'activation_counter':1000,
                     'brake_query':1,'pulse':.625,'rpm_limit':7000,'boost':(17.5,.25)}
        yield state,config,observation,3
    for flags,mode,temperature,bypass,boost in itertools.product((4,7),(0,1,2),(89.999,130.,300.),(False,True),(False,True)):
        config=replace(c,torque=replace(c.torque,third_enabled=True),links=replace(c.links,third_enabled=True))
        yield replace(s,vehicle_flags=flags,thermal_mode=mode,main_temperature=temperature,third_temperature=180.,
                      bypass=bypass,alternate_enabled=boost),config,{'boost':(17.5,.25),'pulse':.5,'brake_query':0,'rpm_limit':6000},5

def mutation_cases():
    s,c=base()
    for flags,domain,stage,name,value in (
        (4,'dispatch','engine_setup','rpm.throttle',.9),
        (4,'dispatch','engine_control','thermal_engagement',.125),
        (4,'dispatch','engagement_inputs','engagement',.75),
        (4,'dispatch','engine_finalize','vehicle_flags',7),
        (7,'torque_update','boost','boost_observation',.5),
        (7,'torque_update','damage','main_temperature',350.),
        (7,'gear_link','damage','engagement',.25),
        (7,'drivetrain_loads','damage','thermal_engagement',.75)):
        state=replace(s,vehicle_flags=flags,alternate_enabled=stage=='boost',gate_one=.9 if domain=='gear_link' else .1,
                      main_temperature=300.,condition=1.1)
        yield state,c,{'boost':(17.5,.25),'pulse':.5,'rpm_limit':2500,'mutations':{(domain,stage):((name,value),)}},4
    for stage,name,value in (('rpm_limit','vehicle_flags',7),('boost','gate_two',.5)):
        yield replace(s,vehicle_flags=6,alternate_enabled=stage=='boost'),c,{
            'boost':(17.5,.25),'pulse':.5,'rpm_limit':2500,
            'mutations':{('torque_update',stage):((name,value),)}},4

class SuppliedPipelineStages:
    def __init__(self,observations):self.observations=observations
    def __call__(self,action,state):
        for name,value in self.observations.get('mutations',{}).get((action.domain,action.stage),()):
            if name.startswith('rpm.'):state.rpm_state=replace(state.rpm_state,**{name[4:]:value})
            else:setattr(state,name,value)
        if action.stage=='interface_query':return self.observations.get('query_'+str(action.code),0)
        if action.stage in ('damage','effect','effect_range'):return None
        return self.observations.get(action.stage,(0.,0.) if action.stage=='boost' else 0)

def verify(executable):
    from unicorn import UC_HOOK_CODE
    o=DynoOracle(executable);cpu,reg=o.cpu,o.reg;owner=o.inputs;config=owner+0x3000;result=owner+0x4000
    interface=owner+0x5000;vtable=owner+0x5100;query=o.stub+0x100
    cpu.mem_write(interface,struct.pack('<I',vtable));cpu.mem_write(vtable+0x10,struct.pack('<I',query));cpu.mem_write(0xa65bd0,struct.pack('<I',interface))
    for address in (0x4b7170,0x549580):cpu.mem_write(address,b'\xdd\x05'+struct.pack('<I',result)+b'\xc3')
    recovered={'torque_update','gear_link','drivetrain_loads','rpm_update','curve_lookup'}
    for address,stage in STAGES.items():
        if stage not in recovered:cpu.mem_write(address,b'\xc3')
    for address,code in ((0x5452c0,b'\xc3'),(0x591180,b'\xc2\x08\x00'),(0x591500,b'\xd9\xee\xc2\x14\x00'),(0x55cfc0,b'\xc3'),(0x54d250,b'\xc3'),(query,b'\xc2\x08\x00')):cpu.mem_write(address,code)
    entries={**STAGES,0x4b7170:'pulse',0x549580:'boost',0x5452c0:'damage',0x591180:'effect',0x591500:'effect_range',0x55cfc0:'brake_query',0x54d250:'rpm_limit',0x535e20:'environment',query:'interface_query'}
    calls=[];observations={}
    def child(cpu,address,size,user):
        stack=cpu.reg_read(reg.UC_X86_REG_ESP);ret=struct.unpack('<I',cpu.mem_read(stack,4))[0]
        domain='dispatch' if 0x545af0<=ret<=0x545eba else 'torque_update' if 0x547120<=ret<=0x547c4a else 'gear_link' if 0x546330<=ret<=0x5464be else 'drivetrain_loads' if 0x5464c0<=ret<=0x546acf else None
        if domain is None:raise AssertionError(('unmodelled parent',hex(ret)))
        stage=entries[address];code=None;values=()
        if stage=='pulse':values=struct.unpack('<4f',cpu.mem_read(stack+4,16))
        elif stage=='rpm_limit':values=struct.unpack('<2i',cpu.mem_read(stack+4,8))
        elif stage in ('effect','effect_range'):
            if cpu.reg_read(reg.UC_X86_REG_ECX)!=owner+0xcc8:raise AssertionError('effect receiver')
            code=struct.unpack('<I',cpu.mem_read(stack+4,4))[0];n=4 if stage=='effect_range' else 1
            values=struct.unpack('<'+'f'*n,cpu.mem_read(stack+8,4*n))
        elif stage=='interface_query':
            code,receiver=struct.unpack('<II',cpu.mem_read(stack+4,8))
            if receiver!=owner or cpu.reg_read(reg.UC_X86_REG_ECX)!=interface:raise AssertionError('interface receiver')
        else:
            receiver=struct.unpack('<I',cpu.mem_read(stack+4,4))[0]
            if receiver!=(config if stage=='curve_lookup' else owner):raise AssertionError((stage,'receiver'))
            if stage in ('curve_lookup','rpm_update','enable_signal'):code=struct.unpack('<i',cpu.mem_read(stack+8,4))[0]
            elif stage=='damage':code,value=struct.unpack('<If',cpu.mem_read(stack+8,8));values=(value,)
        action=PipelineCall(domain,stage,code,values);calls.append(action)
        if stage in recovered|{'environment'}:return
        for name,value in observations.get('mutations',{}).get((domain,stage),()):
            if name.startswith('rpm.'):
                name=name[4:];off=FIELDS[name];fmt='i' if name in INTS else 'f'
            elif name in OWNER_INTS.values():off=next(off for off,n in OWNER_INTS.items() if n==name);fmt='I'
            elif name in OWNER_BYTES.values():off=next(off for off,n in OWNER_BYTES.items() if n==name);fmt='B'
            else:off=next(off for off,n in OWNER_FLOATS.items() if n==name);fmt='f'
            cpu.mem_write(owner+off,struct.pack('<'+fmt,value))
        value=observations.get('query_'+str(code),0) if stage=='interface_query' else observations.get(stage,(0.,0.) if stage=='boost' else 0)
        if stage=='boost':
            value,increment=value;pointer=struct.unpack('<I',cpu.mem_read(stack+8,4))[0];cpu.mem_write(pointer,struct.pack('<f',increment))
        if stage in ('boost','pulse'):cpu.mem_write(result,struct.pack('<d',float(value)))
        elif stage not in ('damage','effect','effect_range'):cpu.reg_write(reg.UC_X86_REG_EAX,int(value)&0xffffffff)
    for address in entries:cpu.hook_add(UC_HOOK_CODE,child,begin=address,end=address)
    count=0;scenarios=0;maximum=0.
    for state,c,observations,ticks in itertools.chain(cases(),mutation_cases()):
        before,data=encode(state,c,config);cpu.mem_write(owner,bytes(before));cpu.mem_write(config,bytes(data))
        for tick in range(ticks):
            if tick:state.counter+=1
            o._reset();calls.clear()
            for address,value in ((0x9aaa64,state.bypass),(0xaa456c,state.counter),(0x9aaa5c,state.environment_override),(0x9aaa60,state.environment_selector_enabled),(0xb12958,state.environment_selector)):cpu.mem_write(address,struct.pack('<i',value))
            cpu.mem_write(0x83f204,struct.pack('<8i',*state.activation_delays))
            stack=o.frame-0x1000;cpu.mem_write(stack,struct.pack('<II',o.stop,owner));cpu.reg_write(reg.UC_X86_REG_ESP,stack)
            o._run(0x545af0,o.stop,count=200000)
            output=update_engine_pipeline(state,c,SuppliedPipelineStages(observations));expected,_=encode(output.state,c,config)
            if len(calls)!=len(output.calls):raise AssertionError((scenarios,tick,'calls',calls,output.calls,state))
            for a,b in zip(calls,output.calls):
                if a.domain!=b.domain or a.stage!=b.stage or a.code!=b.code or len(a.values)!=len(b.values) or any(abs(x-y)>max(.000002,abs(x)*4e-7) for x,y in zip(a.values,b.values)):raise AssertionError((scenarios,tick,'call',a,b,state))
            actual=bytes(cpu.mem_read(owner,len(before)))
            for off in set([off for name,off in FIELDS.items() if name not in INTS]+list(OWNER_FLOATS)):
                a=struct.unpack_from('<f',actual,off)[0];b=struct.unpack_from('<f',expected,off)[0];error=abs(a-b)
                if not math.isfinite(a) or error>max(.0001,abs(a)*4e-7):raise AssertionError((scenarios,tick,hex(off),a,b,state))
                maximum=max(maximum,error);expected[off:off+4]=actual[off:off+4]
            if actual!=expected:
                off=next(i for i,(a,b) in enumerate(zip(actual,expected)) if a!=b);raise AssertionError((scenarios,tick,'owner',hex(off),actual[off:off+4],expected[off:off+4],state))
            if bytes(cpu.mem_read(config,len(data)))!=data:raise AssertionError('config write')
            state=output.state;count+=1
        scenarios+=1
    return {'scenarios':scenarios,'ticks':count,'maximum_absolute_error':maximum,'scope':'whole original dispatcher with actual torque/condition/math/environment/RPM consumers, persistent owner state and exact ordered calls; unknown producers explicitly supplied'}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('executable');print(json.dumps(verify(p.parse_args().executable)))
