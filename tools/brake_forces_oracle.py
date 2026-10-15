"""Complete original brake function; only component effect delivery is substituted."""
import argparse
from dataclasses import replace
import itertools
import json
import math
import struct
from client.brake_forces import BrakeForceState,BrakeForceWheel,update_brake_forces
from tools.brake_thermal_oracle import cases as thermal_cases
from tools.native_oracle import DynoOracle


def cases():
    thermal=next(thermal_cases())
    for speed,service,parking,material,gate in itertools.product(
            (-10,-1,0,.5,1,1.0001,10),(0,.25,1),(False,True),range(4),(False,True)):
        n=material+int(gate)+int(parking)
        front=replace(thermal.front,material_code=material,construction_code=n%2,
            temperature=(100,425,900)[n%3])
        rear=replace(thermal.rear,material_code=(material+1)%4,construction_code=1-n%2,
            temperature=(100,375,800)[n%3])
        t=replace(thermal,front=front,rear=rear,speed=speed,service_control=service,parking_control=parking,
            environment_flag=bool(n%2),environment_code=n%3)
        wheels=tuple(BrakeForceWheel((-1 if i%2 else 1)*(.04 if n%2 else 3),25-i*20,.25+i*.1,
            speed,0 if i==n%4 else 2000+i*300,(i-1)*123,(-.40001,-.4,-.39999,0)[i],
            (6,20,0,1)[i],.7+i*.1,.2+i*.1) for i in range(4))
        base=BrakeForceState(t,wheels,(0,.5,.7)[n%3],(.7,0,.5)[n%3],float(gate),int(gate),
            .7,1.2,.03,n%2,bool(n==4),60 if n%2 else 0)
        yield base
    for spin,front_gate,rear_gate,auxiliary in itertools.product(
            (-.05000001,-.05,0,.05,.05000001),(False,True),(False,True),(False,True)):
        wheels=tuple(replace(w,spin_value=spin,control_angle=(0,-.40001,0,-.40001)[i]) for i,w in enumerate(base.wheels))
        yield replace(base,wheels=wheels,thermal=replace(base.thermal,service_control=0 if auxiliary else .7,
            parking_control=False),auxiliary_flag=auxiliary,front_gate=float(front_gate),rear_gate=int(rear_gate))


def verify(executable):
    from unicorn import UC_HOOK_CODE
    o=DynoOracle(executable);cpu,reg=o.cpu,o.reg
    owner,config=o.inputs,o.inputs+0x3000
    observed={'wear':[],'controller':[],'events':[]}
    # Component update is thiscall with five stack arguments, returning x87.
    component_return=o.stub+0x400;cpu.mem_write(component_return,b'\xd9\xee\xc2\x14\x00')
    def effects(cpu,address,size,user):
        stack=cpu.reg_read(reg.UC_X86_REG_ESP)
        if address==0x591500:
            ret,operation,amount,zero,one,quarter=struct.unpack('<IIfIff',cpu.mem_read(stack,24))
            if cpu.reg_read(reg.UC_X86_REG_ECX)!=owner+0xcc8 or operation not in (5,6) or zero!=0 or one!=1 or quarter!=.25:
                raise AssertionError('unexpected component effect boundary')
            observed['wear'].append((operation,amount));observed['events'].append(('wear',operation,amount))
            cpu.reg_write(reg.UC_X86_REG_EIP,component_return)
        elif address==0x41bd30:
            ret,argument,intensity=struct.unpack('<IIi',cpu.mem_read(stack,12))
            if argument!=owner:raise AssertionError('unexpected controller owner')
            observed['controller'].append(intensity)
            observed['events'].append(('controller',intensity))
            # The actual original controller entry is a no-op RET; execute it.
    cpu.hook_add(UC_HOOK_CODE,effects,begin=0x591500,end=0x591500)
    cpu.hook_add(UC_HOOK_CODE,effects,begin=0x41bd30,end=0x41bd30)
    count,maximum=0,0.0
    for s in cases():
        o._reset()
        for events in observed.values():events.clear()
        t=s.thermal;image=bytearray([0xa5])*0x1d00;data=bytearray([0x5a])*0x700
        struct.pack_into('<I',image,0x1c94,config)
        for off,val in ((0xa90,t.service_control),(0xa2c,t.speed),(0x34c,t.elevation_parameter),
            (0xd10,s.front_quality),(0xd14,s.rear_quality),(0x1910,s.rear_distribution),
            (0xc00,s.pitch_angle),(0x1878,s.drive_factor)):
            struct.pack_into('<f',image,off,val)
        image[0xa6b]=int(t.parking_control);image[0xa69]=2
        struct.pack_into('<I',image,0xae4,0x20 if s.auxiliary_flag else 0)
        struct.pack_into('<i',image,0xa74,s.parking_ramp);struct.pack_into('<i',image,0x354,s.vehicle_code)
        struct.pack_into('<f',data,0x20,t.mass_parameter)
        struct.pack_into('<f',data,0x5e0,s.front_gate);struct.pack_into('<i',data,0x600,s.rear_gate)
        for axle,delta in ((t.front,0),(t.rear,0x20)):
            for off,val in ((0xc7c+delta//8,axle.temperature),(0xc84+delta//8,axle.diameter),
                (0xca4+delta//8,axle.cooling_coefficient),(0xcac+delta//8,axle.heat_capacity_factor)):
                struct.pack_into('<f',image,off,val)
            struct.pack_into('<i',image,0xcb4+delta//8,axle.countdown)
            for off,val in ((0x5c8+delta,axle.thermal_mass),(0x5e4+delta,axle.temperature_limit)):
                struct.pack_into('<f',data,off,val)
            for off,val in ((0x5d4+delta,axle.material_code),(0x5d0+delta,axle.construction_code)):
                struct.pack_into('<I',data,off,val)
        for i,w in enumerate(s.wheels):
            start=0x5fc+i*0x10c
            for off,name in ((0x7c,'spin_value'),(0x88,'spin_adjustment'),(0xbc,'spin_scale'),(0x10,'projected_speed'),
                    (0xd4,'normal_load'),(0xd8,'longitudinal_force'),(0xc,'control_angle'),
                    (0x94,'inertia_addend'),(0xac,'inertia_multiplier')):
                struct.pack_into('<f',image,start+off,getattr(w,name))
            struct.pack_into('<i',image,start+0x58,w.component_code)
            struct.pack_into('<f',image,0xc94+i*4,t.wheels[i].brake_force)
        cpu.mem_write(owner,bytes(image));cpu.mem_write(config,bytes(data))
        for off,val in ((0x9aaa5c,int(t.environment_flag)),(0x9aaa60,1),(0xb12958,t.environment_code)):
            cpu.mem_write(off,struct.pack('<i',val))
        stack=o.frame-0x1000;cpu.mem_write(stack,struct.pack('<II',o.stop,owner));cpu.reg_write(reg.UC_X86_REG_ESP,stack)
        o._run(0x538960,o.stop,count=100000)
        actual=bytes(cpu.mem_read(owner,len(image)));expected=update_brake_forces(s);out=expected.state
        outputs=[(0xc7c,out.thermal.front.temperature),(0xc80,out.thermal.rear.temperature),
            (0xcbc,out.thermal.kinetic_value),(0xcc0,out.thermal.elevation_value)]
        for i,w in enumerate(out.wheels):
            outputs.extend(((0x5fc+i*0x10c+0x88,w.spin_adjustment),(0x5fc+i*0x10c+0xd8,w.longitudinal_force),
                (0xc94+i*4,out.thermal.wheels[i].brake_force)))
        for off,target in outputs:
            value=struct.unpack_from('<f',actual,off)[0];error=abs(value-target)
            if not math.isfinite(value) or error>max(.0005,abs(value)*3e-7):
                raise AssertionError((count,hex(off),value,target,error,s))
            maximum=max(maximum,error);image[off:off+4]=actual[off:off+4]
        for off,target in ((0xcb4,out.thermal.front.countdown),(0xcb8,out.thermal.rear.countdown),(0xa74,out.parking_ramp)):
            value=struct.unpack_from('<i',actual,off)[0]
            if value!=target:raise AssertionError((count,hex(off),value,target))
            image[off:off+4]=actual[off:off+4]
        if actual!=image or bytes(cpu.mem_read(config,len(data)))!=data:raise AssertionError('unexpected state writes')
        wear=tuple((5 if i<2 else 6,amount) for i,amount in expected.wear_events)
        if tuple(observed['wear'])!=wear or tuple(observed['controller'])!=expected.controller_events:
            raise AssertionError((count,'effect calls',observed,wear,expected.controller_events))
        sequence=[('wear',5 if e.slot<2 else 6,e.value) if e.kind=='wear' else ('controller',e.value) for e in expected.events]
        if observed['events']!=sequence:raise AssertionError((count,'interleaved effect order',observed['events'],sequence))
        count+=1
    return {'cases':count,'maximum_absolute_error':maximum,
        'scope':'complete0x538960 with real thermal/fade/quality/world/controller helpers; component effect delivery substituted and recorded'}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('executable')
    print(json.dumps(verify(p.parse_args().executable)))
