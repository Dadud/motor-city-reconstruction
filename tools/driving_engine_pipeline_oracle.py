"""Original vehicle tick with connected engine, controls, loads and environment."""
import argparse
from dataclasses import replace
import json
import math
import struct
from client.driving_engine import DrivingEngine
from client.engine_pipeline import PipelineCall
from tools.driving_controls_oracle import ControlExtension
from tools.driving_pipeline_oracle import verify as verify_pipeline
from tools.engine_pipeline_oracle import (base, encode, OWNER_FLOATS, OWNER_INTS,
    OWNER_BYTES, SuppliedPipelineStages)
from tools.engine_update_oracle import STAGES
from tools.driving_engine_rpm_oracle import FIELDS, INTS
from tools.engine_torque_update_oracle import CONFIG, CONFIG_INTEGERS
from tools.drivetrain_links_oracle import CONFIG as LINK_CONFIG, CONFIG_INT


OWNER_SPANS = {**{off:4 for off in (*OWNER_FLOATS, *OWNER_INTS, *FIELDS.values())},
               **{off:1 for off in OWNER_BYTES}}
RECOVERED = {'torque_update','gear_link','drivetrain_loads','rpm_update','curve_lookup'}


def domain(ret):
    for low, high, name in ((0x545af0,0x545eba,'dispatch'),(0x547120,0x547c4a,'torque_update'),
                           (0x546330,0x5464be,'gear_link'),(0x5464c0,0x546acf,'drivetrain_loads')):
        if low <= ret <= high: return name


class EngineExtension(ControlExtension):
    stages = ControlExtension.stages | DrivingEngine.stages

    def cases(self):
        for index, (s,f,obs) in enumerate(super().cases()):
            s.flags = 4  # Actual controller's flag 2 bypasses the driving branch.
            obs['engine_mutation'] = index % 3 == 0
            yield s,f,obs

    def install(self, o, owner, config, interface, query):
        super().install(o,owner,config,interface,query)
        from unicorn import UC_HOOK_CODE
        self.o,self.config_address,self.interface = o,config,interface
        self.engine_actions=[]; self.engine_ticks=0
        self.double_value=owner+0x4500
        self.double_return=o.stub+0x800
        o.cpu.mem_write(self.double_return,b'\xdd\x05'+struct.pack('<I',self.double_value)+b'\xc3')
        self.entries={**STAGES,0x4b7170:'pulse',0x549580:'boost',0x5452c0:'damage',
                      0x54d250:'rpm_limit',0x535e20:'environment'}
        for address in self.entries:
            o.cpu.hook_add(UC_HOOK_CODE,self.hook,begin=address,end=address)

    def prepare(self,o,owner,config,surfaces,s,f,obs,image,data):
        super().prepare(o,owner,config,surfaces,s,f,obs,image,data)
        f.other_control = self.control.throttle_output
        f.service_control = self.control.brake_output
        f.spin = replace(f.spin, direction_mode=self.control.output_gear)
        e,c=base(); env=self.environment_inputs.environment
        e.vehicle_flags=s.flags; e.selector_index=1; e.engine_flags=self.control.flags
        e.rpm_state=replace(e.rpm_state,rpm=f.spin.rpm,throttle=f.other_control,
            longitudinal_speed=s.local_linear[2])
        e.thermal_mode=f.spin.direction_mode
        e.brake_control=f.service_control; e.curve_torque=self.parameters.torque
        e.effect_motion=s.speed; e.counter=env.wind.simulation_counter
        e.environment_field=env.altitude; e.environment_override=env.cold_environment
        e.environment_selector_enabled=env.weather_enabled; e.environment_selector=env.weather_code
        # The selected gear byte aliases thermal mode; coefficient 3 is an
        # explicitly supplied catalogue entry, not a fabricated gearbox model.
        c=replace(c,links=replace(c.links,mode_coefficients=(.8,1.,.7,.9)))
        engine_image,engine_data=encode(e,c,config)
        for off,size in OWNER_SPANS.items():image[off:off+size]=engine_image[off:off+size]
        for off in (*CONFIG,*CONFIG_INTEGERS,*LINK_CONFIG,*CONFIG_INT,0x68c,0x6c,0x70):
            data[off:off+4]=engine_data[off:off+4]
        data[0x80:0x80+4*len(c.torque.torque_curve)]=engine_data[0x80:0x80+4*len(c.torque.torque_curve)]
        data[0x354:0x364]=engine_data[0x354:0x364]
        off=0x1810+4*e.rpm_state.gear_index;image[off:off+4]=engine_image[off:off+4]
        self.engine_state,self.engine_config=e,c
        self.engine_observations={'rpm_limit':7000,'brake_query':1,'pulse':.5,'boost':(0.,0.)}
        if obs['engine_mutation']:
            self.engine_observations['mutations']={('dispatch','engine_setup'):(('rpm.throttle',.9),),
                ('dispatch','engine_finalize'):(('engine_flags',0xa4),('curve_torque',234.5))}
        self.supplied_engine=SuppliedPipelineStages(self.engine_observations)
        self.engine_actions.clear()
        o.cpu.mem_write(0x9aaa64,struct.pack('<i',int(e.bypass)))
        o.cpu.mem_write(0x83f204,struct.pack('<8i',*e.activation_delays))

    def wrap(self,external):
        controls=super().wrap(external)
        self.engine_driver=DrivingEngine(self.engine_state,self.engine_config,controls,
            self.parameters,self.environment_inputs,
            lambda action,e,s,f:self.supplied_engine(action,e),controls)
        return self.engine_driver

    def _action(self,cpu,reg,stage):
        stack=cpu.reg_read(reg.UC_X86_REG_ESP)
        ret=struct.unpack('<I',cpu.mem_read(stack,4))[0]; parent=domain(ret)
        if parent is None:raise AssertionError(('engine child parent',stage,hex(ret)))
        code=None;values=()
        if stage=='pulse':values=struct.unpack('<4f',cpu.mem_read(stack+4,16))
        elif stage=='rpm_limit':values=struct.unpack('<2i',cpu.mem_read(stack+4,8))
        elif stage in ('effect','effect_range'):
            if cpu.reg_read(reg.UC_X86_REG_ECX)!=self.owner+0xcc8:raise AssertionError('engine effect receiver')
            code=struct.unpack('<I',cpu.mem_read(stack+4,4))[0]
            values=struct.unpack('<'+'f'*(4 if stage=='effect_range' else 1),cpu.mem_read(stack+8,16 if stage=='effect_range' else 4))
        elif stage=='interface_query':
            code,receiver=struct.unpack('<II',cpu.mem_read(stack+4,8))
            if receiver!=self.owner or cpu.reg_read(reg.UC_X86_REG_ECX)!=self.interface:raise AssertionError('engine interface receiver')
        else:
            receiver=struct.unpack('<I',cpu.mem_read(stack+4,4))[0]
            if receiver!=(self.config_address if stage=='curve_lookup' else self.owner):raise AssertionError(('engine receiver',stage))
            if stage in ('curve_lookup','rpm_update','enable_signal'):code=struct.unpack('<i',cpu.mem_read(stack+8,4))[0]
            elif stage=='damage':code,value=struct.unpack('<If',cpu.mem_read(stack+8,8));values=(value,)
        self.engine_actions.append(PipelineCall(parent,stage,code,values))
        if stage in RECOVERED or stage=='environment':return
        for name,value in self.engine_observations.get('mutations',{}).get((parent,stage),()):
            if name.startswith('rpm.'):
                name=name[4:];off=FIELDS[name];fmt='i' if name in INTS else 'f'
            else:
                mapping,fmt=(OWNER_INTS,'I') if name in OWNER_INTS.values() else (OWNER_FLOATS,'f')
                off=next(off for off,n in mapping.items() if n==name)
            cpu.mem_write(self.owner+off,struct.pack('<'+fmt,value))
        value=self.engine_observations.get('query_'+str(code),0) if stage=='interface_query' else self.engine_observations.get(stage,0)
        if stage=='boost':
            value,increment=value;pointer=struct.unpack('<I',cpu.mem_read(stack+8,4))[0]
            cpu.mem_write(pointer,struct.pack('<f',increment))
        if stage in ('boost','pulse'):
            cpu.mem_write(self.double_value,struct.pack('<d',float(value)))
            cpu.reg_write(reg.UC_X86_REG_EIP,self.double_return)
        else:
            cpu.reg_write(reg.UC_X86_REG_EAX,int(value)&0xffffffff)
            cleanup=8 if stage=='effect' else 20 if stage=='effect_range' else 8 if stage=='interface_query' else 0
            cpu.reg_write(reg.UC_X86_REG_ESP,stack+4+cleanup);cpu.reg_write(reg.UC_X86_REG_EIP,ret)

    def hook(self,cpu,address,size,user):
        self._action(cpu,self.o.reg,self.entries[address])

    def nested(self,cpu,reg,stage,ret):
        if stage=='vehicle_gate' and domain(ret):self._action(cpu,reg,'brake_query')
        else:super().nested(cpu,reg,stage,ret)

    def effect(self,cpu,reg,address):
        stack=cpu.reg_read(reg.UC_X86_REG_ESP);ret=struct.unpack('<I',cpu.mem_read(stack,4))[0]
        if domain(ret):
            self._action(cpu,reg,'effect' if address==0x591180 else 'effect_range');return True
        return False

    def mode(self,cpu,reg,operation,argument,interface):
        stack=cpu.reg_read(reg.UC_X86_REG_ESP);ret=struct.unpack('<I',cpu.mem_read(stack,4))[0]
        if domain(ret):self._action(cpu,reg,'interface_query');return True
        return super().mode(cpu,reg,operation,argument,interface)

    def expected(self,image,s,f):
        super().expected(image,s,f)
        e=self.engine_driver.state
        view,_=encode(e,self.engine_config,self.config_address)
        # Controller owns these fields after engine returns. Compare the final
        # controller values rather than overwriting them with an earlier snapshot.
        controller_owned={0x474,0xa2c,0xa44}
        for off,size in OWNER_SPANS.items():
            if off not in controller_owned:image[off:off+size]=view[off:off+size]

    def float_offsets(self):
        return tuple(set(super().float_offsets())|set(OWNER_FLOATS)|{off for name,off in FIELDS.items() if name not in INTS})

    def check(self,o):
        super().check(o)
        expected=self.engine_driver.calls
        if len(self.engine_actions)!=len(expected):raise AssertionError(('engine calls',self.engine_actions,expected))
        for a,b in zip(self.engine_actions,expected):
            if (a.domain,a.stage,a.code)!=(b.domain,b.stage,b.code) or len(a.values)!=len(b.values) or any(not math.isclose(x,y,rel_tol=4e-7,abs_tol=2e-6) for x,y in zip(a.values,b.values)):
                raise AssertionError(('engine action',a,b))
        self.engine_ticks+=int(bool(expected));self.engine_actions.clear()
        # A low-support controller tick does not call the engine; its previous
        # nested actions must not be counted again on the next tick.
        self.engine_driver.calls=()


def verify(executable,actual_support=False):
    extension=EngineExtension()
    result=verify_pipeline(executable,actual_support=actual_support,extension=extension)
    result['engine_ticks']=extension.engine_ticks
    result['scope']='original controller with connected engine torque/condition/RPM, controls, loads, environment and forces; terrain projection, preparation, gear services, engine setup/clutch/wheel drive/finalize, brakes and component delivery supplied'
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('executable');p.add_argument('--actual-support',action='store_true')
    a=p.parse_args();print(json.dumps(verify(a.executable,a.actual_support)))
