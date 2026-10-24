"""Original engine dispatcher/RPM/curve comparison with supplied other children."""
import argparse
from dataclasses import replace
import itertools
import json
import math
import struct
from client.engine_update import EngineUpdateState,update_engine,update_engine_system
from client.driving_engine_rpm import DrivingEngineRPM
from tools.driving_engine_rpm_oracle import FIELDS,INTS
from tools.native_oracle import DynoOracle

STAGES={0x55ce20:'activation_counter',0x540070:'enable_signal',0x55cee0:'start_counter',
    0x540fd0:'control_update',0x548660:'empty_engine_hook',
    0x545ec0:'engine_setup',0x546130:'engine_control',0x546330:'gear_link',0x5464c0:'drivetrain_loads',
    0x546ad0:'engagement_inputs',0x547120:'torque_update',0x547c60:'wheel_drive',0x548050:'engine_finalize',
    0x548fa0:'idle_regulation',0x546c50:'start_acceleration',0x546e70:'rpm_update',0x548f00:'curve_lookup'}
SCALARS={0xe0c:'override_value',0x105c:'motion_metric',0xaa4:'effective_torque',0xaa0:'curve_torque',0xaac:'power',0xb2c:'engagement'}


def cases():
    r=DrivingEngineRPM(600,7000,.3,.4,2400,True,.7,100.,3000*.10471976,3000,6800,2,175.5,20.)
    counter=1000
    for engine_flags,flags,selector,override,control in itertools.product((0,1,0x40,0x41),range(8),range(8),(0.,1.),(False,True)):
        s=EngineUpdateState(r,engine_flags,flags,selector,(32,16,64,48,12,50,40,24),counter,
            override,control,10. if selector%2 else 12.,tuple(100.+i*13.5 for i in range(22)),87.,111.,222.,.4)
        observation={'query_8':selector%2,'query_1':selector%2,
            'activation_counter':counter+256-s.activation_delays[selector]+(1 if selector%3 else 0),
            'start_counter':counter+1 if selector%2 else counter}
        yield s,observation
    for flags,enabled,query,current in itertools.product((2,3,6,7),(0,1),(0,1),(9,10,11,127,128,129)):
        s=EngineUpdateState(r,enabled,flags,0,(32,)*8,current,0.,False,0.,tuple(100.+i*13.5 for i in range(22)))
        yield s,{'query_8':1,'query_1':query,'activation_counter':current+225,'start_counter':current+1}
    for metric in (11.175749,11.17575,11.175751):
        yield EngineUpdateState(r,1,2,0,(32,)*8,1000,0.,False,metric,tuple(100.+i*13.5 for i in range(22))),{}
    for current,activation in ((-0x80000000,0x7fffffff),(0x7fffffff,-0x80000000),(-1,255),(0,256)):
        yield EngineUpdateState(r,0,4,0,(0,)*8,current,0.,False,0.,tuple(100.+i*13.5 for i in range(22))),{'query_8':1,'activation_counter':activation}
    for rpm in (0,499,500,501,999,1000,1001,6500,7999,8000):
        for curve in (tuple(0. for _ in range(22)),tuple(-100.+i*3 for i in range(22))):
            yield EngineUpdateState(replace(r,rpm=rpm),1,6,0,(32,)*8,1000,0.,True,12.,curve),{}


class SuppliedEngineStages:
    def __init__(self,observations):self.observations=observations
    def __call__(self,action,state):
        for name,value in self.observations.get('mutations',{}).get(action.stage,()):
            if name.startswith('rpm.'):
                state.rpm_state=replace(state.rpm_state,**{name[4:]:value})
            else:setattr(state,name,value)
        if action.stage=='interface_query':return self.observations.get(f'query_{action.argument}',0)
        return self.observations.get(action.stage,0)


def mutation_cases():
    base=next(cases())[0]
    for flags,stage,name,value in (
        (4,'interface_query','vehicle_flags',6),
        (4,'interface_query','engine_flags',0x41),
        (4,'engine_setup','rpm.throttle',.123456789),
        (4,'engine_finalize','engagement',.123456789),
        (6,'torque_update','vehicle_flags',3),
        (6,'torque_update','rpm.rpm',501),
        (6,'torque_update','rpm.limiter_rpm',7000),
        (6,'torque_update','effective_torque',-13.),
        (3,'start_acceleration','engine_flags',1),
        (3,'start_acceleration','rpm.acceleration_input',-20.),
        (3,'idle_regulation','rpm.rpm',999),
        (3,'gear_link','engagement',.123456789)):
        s=replace(base,vehicle_flags=flags,control_gate=stage=='idle_regulation')
        if stage!='interface_query' and stage!='start_acceleration':s.engine_flags=1
        yield s,{'query_8':1,'activation_counter':s.current_counter+300,
                 'start_counter':s.current_counter+(1 if stage=='start_acceleration' else 0),
                 'mutations':{stage:((name,value),)}}


def system_cases():
    """The 0x548260 wrapper's control prelude and engagement boundary."""
    for s,observations in itertools.chain(cases(),mutation_cases()):
        for engagement in (0.,.1,.25,.25000003,.5,1.):
            yield replace(s,engagement=engagement),observations


def encode(s,config):
    image=bytearray([0xa5])*0x1d00
    for name,off in FIELDS.items():struct.pack_into('<i' if name in INTS else '<f',image,off,getattr(s.rpm_state,name))
    for off,name in SCALARS.items():struct.pack_into('<f',image,off,getattr(s,name))
    for off,value in ((0xae4,s.engine_flags),(0x474,s.vehicle_flags),(0x464,s.selector_index),(0x1c94,config)):
        struct.pack_into('<I',image,off,value)
    image[0xa87]=int(s.control_gate)
    struct.pack_into('<f',image,0x1810+s.rpm_state.gear_index*4,s.rpm_state.gear_speed_factor)
    data=bytearray([0x5a])*0x300
    struct.pack_into('<ii',data,0x6c,s.rpm_state.idle_rpm,s.rpm_state.configured_max_rpm)
    for i,value in enumerate(s.torque_curve):struct.pack_into('<f',data,0x80+4*i,value)
    return image,data


def verify(executable,vehicle_system=False):
    from unicorn import UC_HOOK_CODE
    o=DynoOracle(executable);cpu,reg=o.cpu,o.reg
    owner,config,interface,vtable=o.inputs,o.inputs+0x3000,o.inputs+0x4000,o.inputs+0x4100
    query=o.stub+0x100;cpu.mem_write(interface,struct.pack('<I',vtable));cpu.mem_write(vtable+0x10,struct.pack('<I',query))
    cpu.mem_write(0xa65bd0,struct.pack('<I',interface))
    calls=[];observations={}
    def child(cpu,address,size,user):
        stack=cpu.reg_read(reg.UC_X86_REG_ESP);ret=struct.unpack('<I',cpu.mem_read(stack,4))[0]
        argument=None
        if address==query:
            stage='interface_query';argument,receiver=struct.unpack('<II',cpu.mem_read(stack+4,8))
            if argument not in (1,8) or receiver!=owner or cpu.reg_read(reg.UC_X86_REG_ECX)!=interface:raise AssertionError('interface arguments')
            value=observations.get(f'query_{argument}',0);cleanup=12
        else:
            stage=STAGES[address];receiver=struct.unpack('<I',cpu.mem_read(stack+4,4))[0]
            if stage=='curve_lookup':
                argument=struct.unpack('<i',cpu.mem_read(stack+8,4))[0]
                if receiver!=config:raise AssertionError('curve receiver')
            else:
                if receiver!=owner:raise AssertionError((stage,'owner receiver',hex(receiver)))
                if stage in ('rpm_update','enable_signal'):argument=struct.unpack('<i',cpu.mem_read(stack+8,4))[0]
            value=observations.get(stage,0);cleanup=4
        calls.append((stage,argument))
        if stage in ('rpm_update','curve_lookup'):return
        for name,change in observations.get('mutations',{}).get(stage,()):
            if name.startswith('rpm.'):
                field=name[4:];offset=FIELDS[field];kind='i' if field in INTS else 'f'
            elif name in ('engine_flags','vehicle_flags'):
                offset=0xae4 if name=='engine_flags' else 0x474;kind='I'
            else:offset=next(off for off,field in SCALARS.items() if field==name);kind='f'
            cpu.mem_write(owner+offset,struct.pack('<'+kind,change))
        cpu.reg_write(reg.UC_X86_REG_EAX,int(value));cpu.reg_write(reg.UC_X86_REG_ESP,stack+cleanup);cpu.reg_write(reg.UC_X86_REG_EIP,ret)
    for entry in (*STAGES,query):cpu.hook_add(UC_HOOK_CODE,child,begin=entry,end=entry)
    count,maximum=0,0.
    corpus=system_cases() if vehicle_system else itertools.chain(cases(),mutation_cases())
    update=update_engine_system if vehicle_system else update_engine
    entry=0x548260 if vehicle_system else 0x545af0
    for s,observations in corpus:
        o._reset();before,data=encode(s,config);cpu.mem_write(owner,bytes(before));cpu.mem_write(config,bytes(data))
        cpu.mem_write(0x83f204,struct.pack('<8i',*s.activation_delays));cpu.mem_write(0xaa456c,struct.pack('<i',s.current_counter))
        calls.clear();stack=o.frame-0x1000;cpu.mem_write(stack,struct.pack('<II',o.stop,owner));cpu.reg_write(reg.UC_X86_REG_ESP,stack)
        o._run(entry,o.stop,count=150000)
        output=update(s,SuppliedEngineStages(observations));expected,_=encode(output.state,config)
        if calls!=[(c.stage,c.argument) for c in output.calls]:raise AssertionError((count,'calls',calls,output.calls,s,observations))
        actual=bytes(cpu.mem_read(owner,len(before)))
        positions=[off for name,off in FIELDS.items() if name not in INTS]+list(SCALARS)
        for position in positions:
            a=struct.unpack_from('<f',actual,position)[0];b=struct.unpack_from('<f',expected,position)[0];error=abs(a-b)
            if not math.isfinite(a) or error>max(.00025,abs(a)*3e-7):raise AssertionError((count,hex(position),a,b,error,s))
            maximum=max(maximum,error);expected[position:position+4]=actual[position:position+4]
        if actual!=expected:
            offset=next(i for i,(a,b) in enumerate(zip(actual,expected)) if a!=b)
            raise AssertionError((count,'unmodelled state',hex(offset),actual[offset:offset+4],expected[offset:offset+4],s))
        if bytes(cpu.mem_read(config,len(data)))!=data:raise AssertionError('configuration mutation')
        count+=1
    return {'cases':count,'maximum_absolute_error':maximum,'scope':('complete 0x548260 vehicle engine controller with recovered RPM/curve plus observed 0x540fd0 and 0x548660 call boundaries; other effects supplied; tracked engine owner/configuration bytes and call order checked' if vehicle_system else 'complete engine dispatcher with actual RPM and curve lookup; other children/interface observations and delay/curve data supplied; exact call order and owner/config bytes')}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('executable');p.add_argument('--vehicle-system',action='store_true');args=p.parse_args();print(json.dumps(verify(args.executable,args.vehicle_system)))
