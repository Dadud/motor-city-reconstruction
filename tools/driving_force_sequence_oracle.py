"""Shared owner-state handoff through six recovered force stages; caller excluded."""
import argparse
from dataclasses import replace
import itertools
import json
import math
import struct
from client.body_moments import BodyMomentState,MomentWheel,accumulate_body_moments
from client.tire_update import update_tires
from client.wheel_force_correction import ForceCorrectionWheel,correct_wheel_forces
from client.wheel_force_orientation import ForceOrientationWheel,orient_wheel_forces
from client.wheel_spin import SpinWheel,WheelSpinState,integrate_wheel_spin
from client.combined_slip import CombinedSlipWheel,CombinedSlipState,limit_combined_slip
from tools.wheel_spin_oracle import WHEEL_FIELDS as SPIN_FIELDS
from tools.native_oracle import DynoOracle
from tools.tire_update_oracle import cases,OWNER_FIELDS,WHEEL_FIELDS


def verify(executable):
    from unicorn import UC_HOOK_CODE
    o=DynoOracle(executable);cpu,reg=o.cpu,o.reg
    owner,config,interface,vtable,query=o.inputs,o.inputs+0x3000,o.inputs+0x4000,o.inputs+0x4100,o.stub+0x100
    cpu.mem_write(interface,struct.pack('<I',vtable));cpu.mem_write(vtable+0x10,struct.pack('<I',query))
    cpu.mem_write(0xa65bd0,struct.pack('<I',interface));cpu.mem_write(0xaa456c,struct.pack('<i',5))
    calls=[]
    def mode(cpu,address,size,user):
        stack=cpu.reg_read(reg.UC_X86_REG_ESP)
        ret,operation,argument=struct.unpack('<III',cpu.mem_read(stack,12))
        if operation!=5 or argument!=owner or cpu.reg_read(reg.UC_X86_REG_ECX)!=interface:
            raise AssertionError('unexpected interface query')
        calls.append(argument);cpu.reg_write(reg.UC_X86_REG_EAX,4)
        cpu.reg_write(reg.UC_X86_REG_ESP,stack+12);cpu.reg_write(reg.UC_X86_REG_EIP,ret)
    cpu.hook_add(UC_HOOK_CODE,mode,begin=query,end=query)
    effects=[];component_return=o.stub+0x400;secondary_return=o.stub+0x410
    cpu.mem_write(component_return,b'\xd9\xee\xc2\x14\x00');cpu.mem_write(secondary_return,b'\xc2\x08\x00')
    def effect(cpu,address,size,user):
        stack=cpu.reg_read(reg.UC_X86_REG_ESP)
        ret,operation,amount=struct.unpack('<IIf',cpu.mem_read(stack,12))
        if cpu.reg_read(reg.UC_X86_REG_ECX)!=owner+0xcc8 or operation not in (1,2):raise AssertionError('unexpected component receiver/operation')
        if address==0x591500:
            a,b,c=struct.unpack('<3f',cpu.mem_read(stack+12,12));effects.append((0,operation,amount,a,b,c))
            cpu.reg_write(reg.UC_X86_REG_EIP,component_return)
        else:
            effects.append((1,operation,amount,0,0,0));cpu.reg_write(reg.UC_X86_REG_EIP,secondary_return)
    for address in (0x591500,0x591180):cpu.hook_add(UC_HOOK_CODE,effect,begin=address,end=address)
    base=next(cases());count,stages,maximum=0,0,0.0
    for speed,control,mask in itertools.product((.25,3,20),(-127,127),range(16)):
        wheels=tuple(replace(w,contact=bool(mask&(1<<i)),normal_load=2000+i*500,
            projected_speed=speed,lateral_force=123,longitudinal_force=211+i) for i,w in enumerate(base.wheels))
        state=replace(base,wheels=wheels,speed=speed,longitudinal_velocity=speed,
            maximum_steering=.08,raw_control=control,mode_observations=(True,)*4,lateral_velocity=.2,yaw_rate=.03)
        image=bytearray([0xa5])*0x1d00;data=bytearray([0x5a])*0x700
        struct.pack_into('<I',image,0x1c94,config);struct.pack_into('<i',image,0xa7c,state.raw_control)
        for offset,name in OWNER_FIELDS:struct.pack_into('<f',image,offset,getattr(state,name))
        for offset,value in ((0xd08,.3),(0xd0c,-.2),(0x18e0,.003),(0x18e4,.002),(0x18e8,.004),
                (0xc0c,.8),(0xbdc,300),(0xbe0,400),(0xbcc,53),(0xa90,1),(0xa94,0),
                (0x18ec,.3),(0x18f0,.35),(0xd18,.7),(0xd1c,.8),(0xbf8,.05),
                (0x1838,.002),(0xd00,.2),(0xd04,.4)):
            struct.pack_into('<f',image,offset,value)
        for offset,value in ((0xa6b,1),(0xa69,2),(0xa88,0)):image[offset]=value
        struct.pack_into('<i',image,0xab4,3000);struct.pack_into('<i',image,0x354,0)
        for i,w in enumerate(wheels):
            start=0x5fc+i*0x10c
            for offset,name in WHEEL_FIELDS:struct.pack_into('<f',image,start+offset,getattr(w,name))
            for offset,value in ((0x74,(i-1)*.2),(0x7c,(i-1)*3),(0x88,25-i*20),
                    (0xbc,.25+i*.1),(0x5c,.7+i*.1),(0x60,.5+i*.1),(0xf4,.125),
                    (0x94,1+i*.1),(0xc0,.5+i*.1)):
                struct.pack_into('<f',image,start+offset,value)
            image[start+0xec]=int(w.contact);image[start+0xc5]=1
            struct.pack_into('<i',image,start+0x58,(0,6,20,1)[i]);struct.pack_into('<i',image,start+0xc8,1)
        for offset,value in ((0x20,1300),(0x2c,state.wheelbase),(0x30,state.front_track),(0x34,1.7),(0x38,.7)):
            struct.pack_into('<f',data,offset,value)
        data[0xe4]=int(state.rear_steering)
        for axle,offset in ((state.front_curves,0x148),(state.rear_curves,0x24c)):
            struct.pack_into('<f',data,offset,axle.angle_coefficient)
            struct.pack_into('<26f',data,offset+8,*axle.primary);struct.pack_into('<26f',data,offset+0x70,*axle.secondary)
        for offset,value in ((0x14c,.02),(0x250,.03),(0x138,-2),(0x23c,3)):struct.pack_into('<f',data,offset,value)
        cpu.mem_write(owner,bytes(image));cpu.mem_write(config,bytes(data));cpu.mem_write(0xa384c8,struct.pack('<I',0))
        spins=[(i-1)*3 for i in range(4)];adjustments=[25-i*20 for i in range(4)]
        scales=[.25+i*.1 for i in range(4)];phases=[.125]*4
        for tick in range(2):
            tire=update_tires(state)
            corrected=correct_wheel_forces(tuple(ForceCorrectionWheel(w.projected_speed,spins[i],adjustments[i],
                scales[i],w.lateral_force,w.longitudinal_force,w.normal_load,.7+i*.1,.5+i*.1,w.contact,True)
                for i,w in enumerate(tire.wheels)),1,0,True,2,False)
            integrated=integrate_wheel_spin(WheelSpinState(tuple(SpinWheel(w.spin_value,w.spin_adjustment,w.spin_scale,
                w.projected_speed,w.normal_load,1+i*.1,.5+i*.1,phases[i],True,w.contact)
                for i,w in enumerate(corrected)),2,False,3000,.002,.3,.35,.02,.03,-2,3,.7,.8,.05,
                1.2,1.5,tire.yaw_rate,tire.lateral_velocity))
            combined,combined_effects=limit_combined_slip(CombinedSlipState(tuple(CombinedSlipWheel(w.slip_ratio,
                tire.wheels[i].lateral_force,tire.wheels[i].longitudinal_force,tire.wheels[i].secondary_response,
                w.normal_load,.7+i*.1,.5+i*.1,w.spin_value,w.spin_scale,w.projected_speed,w.contact,(0,6,20,1)[i],1)
                for i,w in enumerate(integrated.state.wheels)),tire.speed,True,False,.2,.4,0))
            oriented=orient_wheel_forces(tuple(ForceOrientationWheel(tire.wheels[i].steering_angle,
                integrated.state.wheels[i].phase,w.lateral_force,w.longitudinal_force)
                for i,w in enumerate(combined.wheels)),.3,-.2)
            moment=accumulate_body_moments(BodyMomentState(tuple(MomentWheel(w.lateral_force,w.longitudinal_force,
                combined.wheels[i].secondary_response,(i-1)*.2,tire.wheels[i].contact) for i,w in enumerate(oriented)),
                tire.speed,1.2,1.5,1.6,1.7,.7,1300,.003,.002,.004,.8,300,400,53,False))
            tire_outputs=[(offset,getattr(tire,name)) for offset,name in OWNER_FIELDS
                if name in ('yaw_rate','lateral_velocity','lateral_acceleration')]
            for i,w in enumerate(tire.wheels):
                tire_outputs.extend((0x5fc+i*0x10c+offset,getattr(w,name)) for offset,name in WHEEL_FIELDS
                    if name in ('steering_angle','slip_angle','lateral_force','longitudinal_force','secondary_response'))
            correction_outputs=[(0x5fc+i*0x10c+off,value) for i,w in enumerate(corrected)
                for off,value in ((0x7c,w.spin_value),(0x88,w.spin_adjustment))]
            orientation_outputs=[(0x5fc+i*0x10c+off,value) for i,w in enumerate(oriented)
                for off,value in ((0xd0,w.lateral_force),(0xd8,w.longitudinal_force))]
            spin_outputs=[(0x5fc+i*0x10c+off,getattr(w,name)) for i,w in enumerate(integrated.state.wheels)
                for off,name in SPIN_FIELDS if name in ('spin_value','spin_scale','phase','secondary_angle','slip_ratio',
                    'kinetic_value','local_lateral','local_vertical','local_longitudinal')]
            combined_outputs=[(0x5fc+i*0x10c+off,getattr(w,name)) for i,w in enumerate(combined.wheels)
                for off,name in ((0xd0,'lateral_force'),(0xd8,'longitudinal_force'),(0xe0,'secondary_response'))]
            spin_events=tuple((0,1 if slot<2 else 2,amount,0,1,.25) for slot,amount in integrated.wear_events)
            slip_events=tuple((e.operation,1 if e.slot<2 else 2,e.amount,e.parameter_a,e.parameter_b,e.parameter_c) for e in combined_effects)
            for entry,outputs in ((0x53ecf0,tire_outputs),(0x53e130,correction_outputs),
                    (0x5400b0,spin_outputs),(0x53fb30,combined_outputs),
                    (0x540520,orientation_outputs),(0x540710,list(zip((0xa48,0xa4c,0xa50),moment)))):
                effects.clear()
                o._reset();stack=o.frame-0x1000;cpu.mem_write(stack,struct.pack('<II',o.stop,owner))
                cpu.reg_write(reg.UC_X86_REG_ESP,stack);o._run(entry,o.stop,count=100000)
                actual=bytes(cpu.mem_read(owner,len(image)))
                for offset,target in outputs:
                    value=struct.unpack_from('<f',actual,offset)[0];error=abs(value-target)
                    if not math.isfinite(value) or error>max(.0005,abs(value)*3e-7):
                        raise AssertionError((count,tick,hex(entry),hex(offset),value,target,error))
                    maximum=max(maximum,error);image[offset:offset+4]=actual[offset:offset+4]
                if actual!=image or bytes(cpu.mem_read(config,len(data)))!=data:
                    raise AssertionError('unexpected stage writes')
                expected_effects=spin_events if entry==0x5400b0 else slip_events if entry==0x53fb30 else ()
                if tuple(effects)!=expected_effects:raise AssertionError((count,tick,hex(entry),effects,expected_effects))
                stages+=1
            state=replace(tire,wheels=tuple(replace(w,lateral_force=oriented[i].lateral_force,
                longitudinal_force=oriented[i].longitudinal_force,secondary_angle=integrated.state.wheels[i].secondary_angle,
                secondary_response=combined.wheels[i].secondary_response) for i,w in enumerate(tire.wheels)))
            spins=[w.spin_value for w in integrated.state.wheels];adjustments=[w.spin_adjustment for w in corrected]
            scales=[w.spin_scale for w in integrated.state.wheels];phases=[w.phase for w in integrated.state.wheels]
        count+=1
    if len(calls)!=count*2*4:raise AssertionError('query count mismatch')
    return {'scenarios':count,'repeated_calls':2,'stage_comparisons':stages,'maximum_absolute_error':maximum,
        'scope':'shared owner six-stage handoff; original caller/scheduler and input producers excluded; mode and component delivery supplied'}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('executable')
    print(json.dumps(verify(p.parse_args().executable)))
