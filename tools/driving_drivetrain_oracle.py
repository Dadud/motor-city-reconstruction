"""Original complete engine driving branch connected to brakes and tire forces."""
import argparse
from dataclasses import replace
import json
import math
import struct
from client.driving_drivetrain import DrivingDrivetrain
from client.engine_pipeline import PipelineCall
from client.drivetrain_stages import DriveCall
from client.gear_binding import bind_gear_tables
from tools.drivetrain_stages_oracle import base,encode,FLOATS,CONFIG_FLOATS,CONFIG_INTS
from tools.driving_brakes_pipeline_oracle import BrakeExtension
from tools.driving_pipeline_oracle import verify as verify_pipeline


EXTRA_FLOATS=(0xb30,0xb40,0xb44,0xb48,0xb50,0xb68,0xb74,0xb78,0xb7c,0xb80,0xb84,0xb88,0x18b0,0xd5c,0xd60)
DRIVE_STAGES=DrivingDrivetrain.methods


class DrivetrainExtension(BrakeExtension):
    def __init__(self,*,bound_gears=False):
        super().__init__()
        self.bound_gears=bound_gears

    def cases(self):
        for index,(s,f,obs) in enumerate(super().cases()):
            obs['engine_mutation']=False;obs['drive_mask']=(0,5,12,15)[index%4]
            if index%5==0:s.flags|=0x10
            yield s,f,obs

    def install(self,o,owner,config,interface,query):
        super().install(o,owner,config,interface,query)
        self.drive_calls=[];self.drive_calls_total=0
        self.drive_effect_return=o.stub+0xa00;o.cpu.mem_write(self.drive_effect_return,b'\xc2\x08\x00')

    def prepare(self,o,owner,config,surfaces,s,f,obs,image,data):
        super().prepare(o,owner,config,surfaces,s,f,obs,image,data)
        d,c=base()
        c=replace(c,maximum_rpm=self.engine_state.rpm_state.configured_max_rpm,
            gear_ratios=(2.5,0.,2.2,self.parameters.gear_factor),
            gear_losses=self.engine_config.links.mode_coefficients,
            inertia_factors=self.brake_drive_factors,
            speed_factors=(.002,.003,.004,f.spin.gear_multiplier),
            option_one=1.,option_two=1.,option_kind=2,increment_gain=3.,secondary_gain=.2,secondary_kind=1)
        d.local_player=False;d.mode_setting=3
        if self.bound_gears:
            # Finalized tire/configuration observations are synthetic here;
            # produce the shared arrays with the independently verified binder.
            binding=bind_gear_tables(c.maximum_rpm,205,75,15,c.gear_ratios,
                c.gear_losses,c.final_drive)
            count=len(c.gear_ratios)
            c=replace(c,inertia_factors=binding.wheel_inertia_factors[:count],
                speed_factors=binding.speed_per_rpm[:count])
            d.inertia_sum=binding.final_drive_inertia
        d.wheels=[replace(w,distribution=self.brake_state.wheels[i].inertia_multiplier) for i,w in enumerate(d.wheels)]
        self.drive_state,self.drive_config=d,c
        drive_image,drive_data=encode(d,c,config,owner)
        for off in (*EXTRA_FLOATS,0xb64):image[off:off+4]=drive_image[off:off+4]
        image[0xa89]=d.auxiliary_byte
        for i,w in enumerate(d.wheels):
            start=0x5fc+i*0x10c
            for off in (0xa0,0xac,0xb0):image[start+off:start+off+4]=drive_image[start+off:start+off+4]
            driven=bool(obs['drive_mask']&(1<<i));image[start+0xc5]=int(driven)
            f.spin=replace(f.spin,wheels=tuple(replace(old,correction_enabled=driven) if i==j else old
                for j,old in enumerate(f.spin.wheels)))
        for off in (*CONFIG_FLOATS,*CONFIG_INTS):data[off:off+4]=drive_data[off:off+4]
        for off,values,target in ((0x334,c.gear_ratios,data),(0x354,c.gear_losses,data),
                (0x1830,c.speed_factors,image),(0x1870,c.inertia_factors,image)):
            struct.pack_into('<'+'f'*len(values),target,off,*values)
        o.cpu.mem_write(0x9abb04,struct.pack('<I',d.mode_setting))
        self.drive_gate=not obs['resistance_mode'];self.drive_calls.clear()

    def wrap(self,external):
        brakes=super().wrap(external)
        self.drivetrain=DrivingDrivetrain(self.drive_state,self.drive_config,self.control_driver,
            self.parameters,brakes,self.drive_effect,self.engine_driver.execute)
        self.engine_driver.execute=self.drivetrain
        return brakes

    def drive_effect(self,call,d,e,s,f):
        self.expected_drive_calls.append(call)
        return self.drive_gate if call.stage=='vehicle_gate' else None

    def _drive_child(self,cpu,reg,stage):
        stack=cpu.reg_read(reg.UC_X86_REG_ESP);ret=struct.unpack('<I',cpu.mem_read(stack,4))[0]
        code=None;values=()
        if stage=='vehicle_gate':
            if struct.unpack('<I',cpu.mem_read(stack+4,4))[0]!=self.owner:raise AssertionError('drive service receiver')
            cpu.reg_write(reg.UC_X86_REG_EAX,int(self.drive_gate))
        elif stage=='damage':
            owner,code,value=struct.unpack('<IIf',cpu.mem_read(stack+4,12))
            if owner!=self.owner:raise AssertionError('drive damage receiver')
            values=(value,)
        else:
            code,value=struct.unpack('<If',cpu.mem_read(stack+4,8));values=(value,)
            if cpu.reg_read(reg.UC_X86_REG_ECX)!=self.owner+0xcc8:raise AssertionError('drive component receiver')
        self.drive_calls.append(DriveCall(stage,code,values))
        if stage=='effect':cpu.reg_write(reg.UC_X86_REG_EIP,self.drive_effect_return)
        else:cpu.reg_write(reg.UC_X86_REG_ESP,stack+4);cpu.reg_write(reg.UC_X86_REG_EIP,ret)

    def hook(self,cpu,address,size,user):
        stack=cpu.reg_read(self.o.reg.UC_X86_REG_ESP);ret=struct.unpack('<I',cpu.mem_read(stack,4))[0]
        stage=self.entries[address]
        if stage in DRIVE_STAGES and 0x545af0<=ret<=0x545eba:
            self.engine_actions.append(PipelineCall('dispatch',stage));return
        if stage=='damage' and 0x547c60<=ret<0x548050:
            self._drive_child(cpu,self.o.reg,stage);return
        super().hook(cpu,address,size,user)

    def nested(self,cpu,reg,stage,ret):
        if stage=='vehicle_gate' and 0x548050<=ret<0x548260:self._drive_child(cpu,reg,'vehicle_gate')
        else:super().nested(cpu,reg,stage,ret)

    def effect(self,cpu,reg,address):
        stack=cpu.reg_read(reg.UC_X86_REG_ESP);ret=struct.unpack('<I',cpu.mem_read(stack,4))[0]
        if address==0x591180 and 0x547c60<=ret<0x548050:
            self._drive_child(cpu,reg,'effect');return True
        return super().effect(cpu,reg,address)

    def expected(self,image,s,f):
        super().expected(image,s,f)
        d=self.drivetrain.state
        for off in EXTRA_FLOATS:struct.pack_into('<f',image,off,getattr(d,FLOATS[off]))
        struct.pack_into('<i',image,0xb64,d.hold_ticks)
        for i,w in enumerate(d.wheels):
            for off,value in ((0xa0,w.conversion),(0xac,w.distribution),(0xb0,w.torque)):
                struct.pack_into('<f',image,0x5fc+i*0x10c+off,value)

    def float_offsets(self):
        return (*super().float_offsets(),*EXTRA_FLOATS,
            *(0x5fc+i*0x10c+off for i in range(4) for off in (0xa0,0xac,0xb0)))

    def ready(self,image,data):
        super().ready(image,data);self.expected_drive_calls=[]

    def check(self,o):
        super().check(o)
        if len(self.drive_calls)!=len(self.expected_drive_calls):raise AssertionError(('drive call count',self.drive_calls,self.expected_drive_calls))
        for a,b in zip(self.drive_calls,self.expected_drive_calls):
            if (a.stage,a.code)!=(b.stage,b.code) or len(a.values)!=len(b.values) or any(not math.isclose(x,y,rel_tol=4e-7,abs_tol=1e-7) for x,y in zip(a.values,b.values)):
                raise AssertionError(('drive action',a,b))
        self.drive_calls_total+=len(self.drive_calls)
        self.drive_calls.clear();self.expected_drive_calls.clear();self.drivetrain.calls=()


def verify(executable,actual_support=False,*,bound_gears=False):
    extension=DrivetrainExtension(bound_gears=bound_gears);result=verify_pipeline(executable,actual_support=actual_support,extension=extension)
    result.update(engine_ticks=extension.engine_ticks,brake_ticks=extension.brake_ticks,
        drivetrain_child_observations=extension.drive_calls_total,producer_bound_gears=bound_gears,
        scope='original controller and all eight engine driving children including clutch, coupling, request, wheel torque distribution and force application; brakes/loads/environment/tires connected; terrain, remaining preparation, gear services, queries and component effects supplied')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('executable');p.add_argument('--actual-support',action='store_true')
    p.add_argument('--bound-gears',action='store_true',help='derive shared gear tables with recovered startup producer')
    a=p.parse_args();print(json.dumps(verify(a.executable,a.actual_support,bound_gears=a.bound_gears)))
