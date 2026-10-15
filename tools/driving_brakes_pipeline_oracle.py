"""Original shared vehicle tick with recovered brakes, engine and tire forces."""
import argparse
from dataclasses import replace
import json
import math
import struct
from client.driving_brakes import DrivingBrakes
from client.tire_response import f32
from tools.brake_forces_oracle import cases as brake_cases
from tools.driving_engine_pipeline_oracle import EngineExtension
from tools.driving_pipeline_oracle import verify as verify_pipeline


BRAKE_FLOATS=(0xc7c,0xc80,0xcbc,0xcc0,0xc94,0xc98,0xc9c,0xca0)
BRAKE_INTS=(0xcb4,0xcb8,0xa74)


def write_brake_outputs(image,b):
    for off,value in ((0xc7c,b.thermal.front.temperature),(0xc80,b.thermal.rear.temperature),
            (0xcbc,b.thermal.kinetic_value),(0xcc0,b.thermal.elevation_value)):
        struct.pack_into('<f',image,off,value)
    for i,w in enumerate(b.thermal.wheels):struct.pack_into('<f',image,0xc94+4*i,w.brake_force)
    for off,value in ((0xcb4,b.thermal.front.countdown),(0xcb8,b.thermal.rear.countdown),(0xa74,b.parking_ramp)):
        struct.pack_into('<i',image,off,value)


class BrakeExtension(EngineExtension):
    stages=EngineExtension.stages|DrivingBrakes.stages

    def install(self,o,owner,config,interface,query):
        super().install(o,owner,config,interface,query)
        from unicorn import UC_HOOK_CODE
        self.brake_events=[];self.brake_ticks=0;self.brake_event_count=0
        self.brake_return=o.stub+0x900
        o.cpu.mem_write(self.brake_return,b'\xd9\xee\xc2\x14\x00')
        def controller(cpu,address,size,user):
            stack=cpu.reg_read(o.reg.UC_X86_REG_ESP)
            ret,receiver,value=struct.unpack('<IIi',cpu.mem_read(stack,12))
            if not 0x538960<=ret<0x539790 or receiver!=owner:raise AssertionError('brake controller receiver')
            self.brake_events.append(('controller',value))
            # Original function is RET, retained unchanged.
        o.cpu.hook_add(UC_HOOK_CODE,controller,begin=0x41bd30,end=0x41bd30)
        def boundary(cpu,address,size,user):
            if address==0x538960:self.brake_before=bytes(cpu.mem_read(owner,0x2000))
            else:self.brake_after=bytes(cpu.mem_read(owner,0x2000))
        for address in (0x538960,0x53ecf0):o.cpu.hook_add(UC_HOOK_CODE,boundary,begin=address,end=address)
        def combined(cpu,address,size,user):self.combined_before=bytes(cpu.mem_read(owner,0x2000))
        o.cpu.hook_add(UC_HOOK_CODE,combined,begin=0x53fb30,end=0x53fb30)

    def prepare(self,o,owner,config,surfaces,s,f,obs,image,data):
        super().prepare(o,owner,config,surfaces,s,f,obs,image,data)
        b=next(b for b in brake_cases() if b.thermal.front.material_code==2 and b.thermal.front.temperature==900)
        b=replace(b,pitch_angle=self.parameters.pitch,vehicle_code=s.environment_mode,
            wheels=tuple(replace(w,inertia_addend=spin.kinetic_parameter) for w,spin in zip(b.wheels,f.spin.wheels)))
        self.brake_state=b;self.brake_events.clear()
        self.brake_drive_factors=(.2,.4,.8,1.2)
        # Exercise enabled/disabled weather with the actual original selector.
        env=self.environment_inputs.environment
        weather=not obs['resistance_mode']
        self.environment_inputs.environment=replace(env,weather_enabled=weather)
        o.cpu.mem_write(0x9aaa60,struct.pack('<i',int(weather)))
        for off,value in ((0xd10,b.front_quality),(0xd14,b.rear_quality),
                (0x1910,b.rear_distribution)):
            struct.pack_into('<f',image,off,value)
        struct.pack_into('<4f',image,0x1870,*self.brake_drive_factors)
        struct.pack_into('<f',data,0x5e0,b.front_gate);struct.pack_into('<i',data,0x600,b.rear_gate)
        for axle,delta in ((b.thermal.front,0),(b.thermal.rear,0x20)):
            for off,value in ((0xc84+delta//8,axle.diameter),(0xca4+delta//8,axle.cooling_coefficient),
                    (0xcac+delta//8,axle.heat_capacity_factor)):
                struct.pack_into('<f',image,off,value)
            for off,value in ((0x5c8+delta,axle.thermal_mass),(0x5e4+delta,axle.temperature_limit)):
                struct.pack_into('<f',data,off,value)
            for off,value in ((0x5d4+delta,axle.material_code),(0x5d0+delta,axle.construction_code)):
                struct.pack_into('<i',data,off,value)
        for i,w in enumerate(b.wheels):struct.pack_into('<f',image,0x5fc+0x10c*i+0xac,w.inertia_multiplier)
        write_brake_outputs(image,b)

    def wrap(self,external):
        engine=super().wrap(external)
        self.brake_driver=DrivingBrakes(self.brake_state,self.brake_drive_factors,self.control_driver,self.parameters,
            self.environment_inputs,self.record,engine)
        self.expected_brake_events=[]
        return self.brake_driver

    def record(self,events,s,f,brakes):
        self.force_inputs=f
        entry=self.brake_driver.last_input
        for off,value in ((0xa90,entry.thermal.service_control),(0xa2c,entry.thermal.speed),
                (0xc7c,entry.thermal.front.temperature),(0xd10,entry.front_quality),
                (0x5fc+0x88,entry.wheels[0].spin_adjustment),(0x5fc+0xac,entry.wheels[0].inertia_multiplier),
                (0x5fc+0x94,entry.wheels[0].inertia_addend)):
            actual=struct.unpack_from('<f',self.brake_before,off)[0]
            if not math.isclose(actual,value,rel_tol=4e-7,abs_tol=.0005):raise AssertionError(('brake input',hex(off),actual,value))
        for i,w in enumerate(brakes.wheels):
            for offset,value in ((0x88,w.spin_adjustment),(0xd8,w.longitudinal_force)):
                actual=struct.unpack_from('<f',self.brake_after,0x5fc+i*0x10c+offset)[0]
                if not math.isclose(actual,value,rel_tol=4e-7,abs_tol=.0005):
                    raise AssertionError(('brake boundary',i,hex(offset),actual,value))
        self.expected_brake_events.extend(('wear',5 if e.slot<2 else 6,e.value) if e.kind=='wear'
            else ('controller',e.value) for e in events)
        self.brake_ticks+=1

    def effect(self,cpu,reg,address):
        stack=cpu.reg_read(reg.UC_X86_REG_ESP);ret=struct.unpack('<I',cpu.mem_read(stack,4))[0]
        if address==0x591500 and 0x5398d0<=ret<0x539940:
            _,operation,amount,zero,one,quarter=struct.unpack('<IIfIff',cpu.mem_read(stack,24))
            if cpu.reg_read(reg.UC_X86_REG_ECX)!=self.owner+0xcc8 or operation not in (5,6) or (zero,one,quarter)!=(0,1.,.25):
                raise AssertionError('brake wear receiver/arguments')
            self.brake_events.append(('wear',operation,amount))
            cpu.reg_write(reg.UC_X86_REG_EIP,self.brake_return);return True
        return super().effect(cpu,reg,address)

    def expected(self,image,s,f):
        super().expected(image,s,f)
        write_brake_outputs(image,self.brake_driver.state)

    def float_offsets(self):return (*super().float_offsets(),*BRAKE_FLOATS)

    def check(self,o):
        super().check(o)
        if len(self.brake_events)!=len(self.expected_brake_events):
            raise AssertionError(('brake event count',self.brake_events,self.expected_brake_events))
        for a,b in zip(self.brake_events,self.expected_brake_events):
            if a[:-1]!=b[:-1] or not math.isclose(a[-1],b[-1],abs_tol=3e-10,rel_tol=4e-7):
                raise AssertionError(('brake event order/arguments',a,b))
        self.brake_event_count+=len(self.brake_events)
        self.brake_events.clear();self.expected_brake_events.clear()

    def failure_detail(self):
        return [(i,struct.unpack_from('<f',self.combined_before,0x5fc+i*0x10c+0x7c)[0],
            w.spin_value,struct.unpack_from('<f',self.combined_before,0x5fc+i*0x10c+0x10)[0],
            w.projected_speed,w.spin_scale) for i,w in enumerate(self.force_inputs.spin.wheels)]

    def conditioned_secondary(self,slot,actual,expected):
        # Subtracting projected rotation from spin amplifies an already checked
        # one-ULP carried spin difference. Both observations must be EXACT for
        # their own source fields; no force/velocity/event tolerance is widened.
        start=0x5fc+slot*0x10c
        spin=struct.unpack_from('<f',self.combined_before,start+0x7c)[0]
        speed=struct.unpack_from('<f',self.combined_before,start+0x10)[0]
        scale=struct.unpack_from('<f',self.combined_before,start+0xbc)[0]
        py=self.force_inputs.spin.wheels[slot]
        def observation(spin,speed,scale):return f32(min(f32(13.4109),abs(f32(spin-speed/scale)))*.03125)
        return actual==observation(spin,speed,scale) and expected==observation(py.spin_value,py.projected_speed,py.spin_scale)


def verify(executable,actual_support=False):
    extension=BrakeExtension()
    result=verify_pipeline(executable,actual_support=actual_support,extension=extension)
    result.update(engine_ticks=extension.engine_ticks,brake_ticks=extension.brake_ticks,
        brake_events=extension.brake_event_count,
        scope='original controller with actual brakes/thermal/fade/world selector, engine torque/condition/RPM, controls, loads, environment and forces; terrain projection, preparation, gear services, engine setup/clutch/wheel drive/finalize and component delivery supplied; brake effects checked in interleaved order')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('executable');p.add_argument('--actual-support',action='store_true')
    a=p.parse_args();print(json.dumps(verify(a.executable,a.actual_support)))
