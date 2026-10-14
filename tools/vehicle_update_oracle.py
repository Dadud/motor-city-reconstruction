"""Full original controller comparison; supplied child stages, no host execution."""
import argparse
from copy import deepcopy
from dataclasses import fields
import itertools
import json
import math
import struct
from client.vehicle_update import VehicleUpdateState,update_vehicle,apply_linear_update
from tools.native_oracle import DynoOracle

STAGES={
    0x55fc30:'global_mode',0x54ebe0:'prepare_vehicle',0x53d320:'predict_support',
    0x427da0:'support_bookkeeping',0x535fe0:'tilted_motion',0x548260:'refresh_motion',
    0x402a20:'flagged_motion',0x536250:'body_forces',0x540c30:'linear_update',
    0x536480:'body_moment_inputs',0x53d920:'normal_loads',0x53e390:'grip_observation',
    0x55cfc0:'vehicle_gate',0x53e030:'project_wheels',0x540fd0:'aero',
    0x53e680:'load_transfer',0x53e980:'suspension_loads',0x53e3d0:'resistance',
    0x545af0:'engine',0x538960:'brakes',0x53ecf0:'tires',0x53e130:'wheel_correction',
    0x5400b0:'wheel_spin',0x53fb30:'combined_slip',0x540520:'force_orientation',
    0x540710:'body_moments',0x4a0440:'post_vehicle',0x55fc10:'followup_enabled',
    0x55fc20:'followup_ready',0x5387d0:'followup',0x541930:'steering_angle'}
SCALARS={0xc4:'attitude',0xa2c:'speed',0x3b4:'alternate_speed',0xbc8:'secondary_angle',
    0xbe8:'turning_radius_y',0xbec:'turning_radius_x',0x54:'inverse_mass',0x50:'mass',
    0xbe4:'gravity_force',0xbcc:'lateral_contribution',0xbd4:'longitudinal_contribution',
    0x18b8:'front_lever',0x18bc:'rear_lever',0xbdc:'front_moment',0xbe0:'rear_moment',
    0xbd8:'body_moment',0x18e0:'angular_scale',0x18b4:'maximum_steering',0xd00:'front_grip_gate',0xd04:'rear_grip_gate'}
VECTORS={0x14:'linear_velocity',0x38:'angular_velocity',0x20:'linear_acceleration',
    0x44:'angular_acceleration',0x2c:'extra_acceleration',0xa3c:'local_linear',
    0xa54:'local_angular',0xa30:'local_acceleration',0xa48:'local_angular_acceleration',
    0xc34:'to_local',0xc10:'to_world'}
WHEEL_SCALARS={0x58:'surface_class',0x5c:'primary_coefficient',0x60:'secondary_coefficient',
    0xfc:'base_grip',0xf8:'quality',0xbc:'spin_scale',0x7c:'spin',0x10:'projected_speed',
    0x64:'local_lateral',0xf4:'phase',0:'primary_angle',0xb8:'clear_reference',0xe8:'clear_threshold'}


def cases():
    """Authored supplied-state corpus, including independent successive gates."""
    variants=[]
    for mode in (0,1):variants.append(('inactive',0,1,0,mode,0,0,(False,False)))
    for mask,mode in itertools.product(range(16),(0,1)):
        if mode:variants.append(('alternate',mask,1,0,mode,0,0,(False,False)))
        variants.append(('tilted',mask,.84,0,0,0,0,(False,False)))
        variants.append(('tilted',mask,1,0,0,0,1,(False,False)))
    for flags in (2,0x200,0x202):variants.append(('flagged',15,1,flags,0,0,0,(False,False)))
    for mask,air in itertools.product((0,1,2,4,8),(0,1)):
        variants.append(('low_support',mask,1,0,0,air,0,(False,False)))
    for mask,environment,gates in itertools.product(range(16),(0,1,2),itertools.product((False,True),repeat=2)):
        if mask.bit_count()>=2:variants.append(('supported',mask,1,0,0,0,environment,gates))
    for index,(branch,mask,attitude,flags,mode,air,environment,gates) in enumerate(variants):
        for velocity in (0.,.002,4.,20.,-20.):
            s=VehicleUpdateState(active=branch!='inactive',tilted=branch=='tilted' and attitude==1,
                attitude=attitude,flags=flags,local_linear=(velocity*.2,.7,velocity),
                linear_velocity=(.2,-1.3,velocity),angular_velocity=(0.,.001,0.) if velocity==0 else (.02,-.03,.04),
                linear_acceleration=(.3,-.2,.5),extra_acceleration=(.1,.2,-.3),
                angular_acceleration=(.01,.02,.03),local_acceleration=(.2,.3,.4),
                local_angular=(.1,.002,.3),local_angular_acceleration=(.01,.02,.03),
                to_local=(.8,0.,-.6,0.,1.,0.,.6,0.,.8),to_world=(.8,0.,.6,0.,1.,0.,-.6,0.,.8),
                alternate_speed=velocity,front_lever=1.2,rear_lever=1.5,front_moment=22,rear_moment=-17,
                body_moment=15,angular_scale=.004,lateral_contribution=.0001 if velocity==0 else 8,
                longitudinal_contribution=-13,front_grip_gate=.1 if index%2 else .2,rear_grip_gate=.3,
                environment_mode=environment,fallback_surface=10,support_count=mask.bit_count(),
                orientation_disabled=bool(index%2),grip_boost=bool(index%3==0),
                surface_coefficients=tuple(.4+i*.015 for i in range(32)))
            for i,w in enumerate(s.wheels):
                w.contact=bool(mask&(1<<i));w.force=(30+i*7,0. if index%4==i else 1500.+i*200,120+i*30)
                w.surface_record=None if index%4==i else (6,20,1,3)[i]|0xa0
                w.base_grip=.8+i*.1;w.quality=.9+i*.05;w.wear_mode=(i+index)%2;w.tire_type=5 if i%2 else 0
                w.spin_scale=0. if branch=='alternate' and i==index%4 else .3+i*.02
                w.spin=velocity*3+i;w.projected_speed=velocity+i;w.local_lateral=.1*i
                w.phase=.25+i*.01;w.primary_angle=.012*i
                w.clear_reference=.5;w.clear_threshold=-.5001 if index%4==i else -.4999
            observations={'global_mode':(mode,)+(int(index%7==0),)*4,'vehicle_gate':gates,
                'airborne_mode':air,'followup_enabled':bool(index%2),'followup_ready':bool(index%3),
                'steering_angle':.03125,'grip_observation':.699 if index%2 else .701}
            yield s,observations,branch


class SuppliedStages:
    def __init__(self,observations):self.observations=observations;self.counts={}
    def result(self,stage):
        value=self.observations.get(stage,0)
        count=self.counts.get(stage,0);self.counts[stage]=count+1
        return value[count] if isinstance(value,tuple) else value
    def __call__(self,action,state):
        for name,value in self.observations.get('mutations',{}).get(action.stage,()):
            if name=='contacts':
                for i,w in enumerate(state.wheels):w.contact=bool(value&(1<<i))
            elif name=='forces':
                for w,force in zip(state.wheels,value):w.force=tuple(map(float,force))
            else:setattr(state,name,deepcopy(value))
        if action.stage=='linear_update' and self.observations.get('execute_linear',False):
            apply_linear_update(state,self.observations['linear_gate'])
        return self.result(action.stage)


def mutation_cases():
    base=next(s for s,o,b in cases() if b=='supported' and all(w.contact for w in s.wheels))
    queries={'global_mode':(0,0,0,0,0),'vehicle_gate':(True,True),
        'airborne_mode':0,'followup_enabled':True,'followup_ready':True,
        'steering_angle':.03125,'grip_observation':.6}
    for stage,name,value,branch in (
            ('prepare_vehicle','attitude',.7,'tilted'),
            ('prepare_vehicle','attitude',.849999999,'supported'),
            ('prepare_vehicle','attitude',.84999996,'tilted'),
            ('predict_support','contacts',0,'low_support'),
            ('predict_support','contacts',1,'low_support'),
            ('predict_support','contacts',3,'supported'),
            ('normal_loads','forces',((1.,100.,2.),)*4,'supported'),
            ('tires','forces',((20.,300.,-40.),)*4,'supported'),
            ('body_moments','local_angular_acceleration',(.03,.04,-.05),'supported'),
            ('linear_update','linear_velocity',(11.,-12.,13.),'supported')):
        for orientation in (False,True):
            s=deepcopy(base);s.orientation_disabled=orientation
            yield s,{**queries,'mutations':{stage:((name,value),)}},branch


def connected_cases():
    for s,observations,branch in itertools.chain(cases(),mutation_cases()):
        if branch not in ('low_support','supported'):continue
        for gate in (False,True):
            yield s,{**observations,'execute_linear':True,'linear_gate':gate},branch


def encode(s,owner,surfaces):
    image=bytearray([0xa5])*0x1d00
    image[4]=int(s.active);image[5]=int(s.tilted)
    for off,name in SCALARS.items():struct.pack_into('<f',image,off,getattr(s,name))
    for off,name in VECTORS.items():
        value=getattr(s,name);struct.pack_into('<'+'f'*len(value),image,off,*value)
    for off,value in ((0x474,s.flags),(0x354,s.environment_mode),(0x404,s.fallback_surface),(0xc08,s.support_count)):
        struct.pack_into('<I',image,off,value)
    for i,w in enumerate(s.wheels):
        start=0x5fc+i*0x10c
        for off,name in WHEEL_SCALARS.items():
            struct.pack_into('<I' if name=='surface_class' else '<f',image,start+off,getattr(w,name))
        image[start+0xec]=int(w.contact)
        struct.pack_into('<3f',image,start+0xd0,*w.force)
        for off,value in ((0xc8,w.wear_mode),(0xcc,w.tire_type)):struct.pack_into('<i',image,start+off,value)
        struct.pack_into('<I',image,start+0x20,0 if w.surface_record is None else surfaces+i*16)
    return image


def verify(executable):
    from unicorn import UC_HOOK_CODE
    o=DynoOracle(executable);cpu,reg=o.cpu,o.reg
    owner,surfaces,interface,vtable=o.inputs,o.inputs+0x3000,o.inputs+0x4000,o.inputs+0x4100
    air_query=o.stub+0x100;float_return=o.stub+0x200;float_value=o.inputs+0x4200
    cpu.mem_write(interface,struct.pack('<I',vtable));cpu.mem_write(vtable+0x10,struct.pack('<I',air_query))
    cpu.mem_write(0xa65bd0,struct.pack('<I',interface))
    cpu.mem_write(float_return,b'\xd9\x05'+struct.pack('<I',float_value)+b'\xc3')
    actual_calls=[];driver=None
    def child(cpu,address,size,user):
        stage='airborne_mode' if address==air_query else STAGES[address]
        stack=cpu.reg_read(reg.UC_X86_REG_ESP);ret=struct.unpack('<I',cpu.mem_read(stack,4))[0]
        slot=None
        if stage=='airborne_mode':
            operation,argument=struct.unpack('<II',cpu.mem_read(stack+4,8))
            if operation!=0x10 or argument!=owner or cpu.reg_read(reg.UC_X86_REG_ECX)!=interface:raise AssertionError('air query arguments')
        elif stage not in ('global_mode','followup_enabled','followup_ready'):
            if struct.unpack('<I',cpu.mem_read(stack+4,4))[0]!=owner:raise AssertionError(('child receiver',stage))
            if stage=='grip_observation':slot=struct.unpack('<I',cpu.mem_read(stack+8,4))[0]
        internal_gate=stage=='vehicle_gate' and 0x540c30<=ret<0x540f00
        if not internal_gate:actual_calls.append((stage,slot))
        value=driver.observations['linear_gate'] if internal_gate else driver.result(stage)
        for name,change in driver.observations.get('mutations',{}).get(stage,()):
            if name=='contacts':
                for i in range(4):cpu.mem_write(owner+0x5fc+i*0x10c+0xec,bytes([int(bool(change&(1<<i)))]))
            elif name=='forces':
                for i,force in enumerate(change):cpu.mem_write(owner+0x5fc+i*0x10c+0xd0,struct.pack('<3f',*force))
            elif name in SCALARS.values():
                offset=next(k for k,v in SCALARS.items() if v==name);cpu.mem_write(owner+offset,struct.pack('<f',change))
            elif name in VECTORS.values():
                offset=next(k for k,v in VECTORS.items() if v==name);cpu.mem_write(owner+offset,struct.pack('<'+'f'*len(change),*change))
            else:raise AssertionError('unsupported supplied mutation')
        if stage=='linear_update' and driver.observations.get('execute_linear',False):return
        if stage in ('steering_angle','grip_observation','engine'):
            cpu.mem_write(float_value,struct.pack('<f',value));cpu.reg_write(reg.UC_X86_REG_EIP,float_return)
        else:
            cpu.reg_write(reg.UC_X86_REG_EAX,int(value));cpu.reg_write(reg.UC_X86_REG_ESP,stack+(12 if stage=='airborne_mode' else 4))
            cpu.reg_write(reg.UC_X86_REG_EIP,ret)
    for entry in (*STAGES,air_query):cpu.hook_add(UC_HOOK_CODE,child,begin=entry,end=entry)
    count,maximum,branches=0,0.,{}
    for s,observations,branch in itertools.chain(cases(),mutation_cases(),connected_cases()):
        o._reset();image=encode(s,owner,surfaces)
        for i,w in enumerate(s.wheels):cpu.mem_write(surfaces+i*16+4,bytes([w.surface_record or 0]))
        cpu.mem_write(owner,bytes(image))
        cpu.mem_write(0xa384c8,struct.pack('<I',int(s.orientation_disabled)))
        cpu.mem_write(0xa65bce,bytes([int(s.grip_boost)]))
        for i,coefficient in enumerate(s.surface_coefficients):cpu.mem_write(0x89bf70+i*8,struct.pack('<f',coefficient))
        actual_calls.clear();driver=SuppliedStages(observations)
        stack=o.frame-0x1000;cpu.mem_write(stack,struct.pack('<II',o.stop,owner));cpu.reg_write(reg.UC_X86_REG_ESP,stack)
        o._run(0x53c140,o.stop,count=100000)
        output=update_vehicle(s,SuppliedStages(observations))
        if output.branch!=branch:raise AssertionError(('branch',branch,output.branch))
        expected_calls=[(c.stage,c.slot) for c in output.calls]
        if expected_calls!=actual_calls:raise AssertionError((count,branch,'calls',expected_calls,actual_calls))
        actual=bytes(cpu.mem_read(owner,len(image)));expected=encode(output.state,owner,surfaces)
        positions=[off for off in SCALARS]
        for off,name in VECTORS.items():positions.extend(off+4*i for i in range(len(getattr(s,name))))
        for i,w in enumerate(s.wheels):
            start=0x5fc+i*0x10c
            positions.extend(start+off for off,name in WHEEL_SCALARS.items() if name!='surface_class')
            positions.extend(start+0xd0+4*j for j in range(3))
            struct.pack_into('<3f',image,start+0xd0,*w.force)
            struct.pack_into('<3f',expected,start+0xd0,*output.state.wheels[i].force)
        for position in positions:
            a=struct.unpack_from('<f',actual,position)[0];b=struct.unpack_from('<f',expected,position)[0]
            error=abs(a-b)
            if not math.isfinite(a) or error>max(.0005,abs(a)*4e-7):raise AssertionError((count,branch,hex(position),a,b,error))
            maximum=max(maximum,error);expected[position:position+4]=actual[position:position+4]
        if actual!=expected:
            offset=next(i for i,(a,b) in enumerate(zip(actual,expected)) if a!=b)
            raise AssertionError(('unexpected owner mutation',count,branch,hex(offset),actual[offset:offset+8],expected[offset:offset+8]))
        branches[branch]=branches.get(branch,0)+1;count+=1
    return {'cases':count,'branches':branches,'maximum_absolute_error':maximum,
        'scope':'complete 0x53c140 controller plus connected 0x540c30 paths; other child stages/gate observations and surface table supplied; exact ordered calls and owner byte checks'}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('executable')
    print(json.dumps(verify(p.parse_args().executable)))
