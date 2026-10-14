"""Complete original wheel integration; component-event delivery is supplied."""
import argparse
import itertools
import json
import math
import struct
from client.wheel_spin import SpinWheel,WheelSpinState,integrate_wheel_spin
from tools.native_oracle import DynoOracle


def cases():
    for spin,adjustment,speed,mode,mask,override in itertools.product(
            (-30,0,30),(-100,0,100),(-20,0,20),(0,1,2),range(16),(False,True)):
        wheels=tuple(SpinWheel(spin*(i-1),adjustment,.3+i*.02,speed,(0,2000,10000,30000)[i],
            1+i*.1,.5+i*.1,(i-1)*.125,bool(mask&(1<<i)),bool(mask&(1<<i))) for i in range(4))
        yield WheelSpinState(wheels,mode,override,3000,.002,.3,.35,.02,.03,-2,3,.7,.8,.05,1.2,1.5,.03,.2)


OWNER_FIELDS=((0x18ec,'front_scale'),(0x18f0,'rear_scale'),(0xd18,'front_quality'),(0xd1c,'rear_quality'),
    (0xbf8,'body_secondary_angle'),(0x18b8,'front_lever'),(0x18bc,'rear_lever'),(0xa58,'yaw_rate'),(0xa3c,'lateral_velocity'))
WHEEL_FIELDS=((0x7c,'spin_value'),(0x88,'spin_adjustment'),(0xbc,'spin_scale'),(0x10,'projected_speed'),
    (0xd4,'normal_load'),(0x94,'kinetic_parameter'),(0xc0,'ratio_denominator'),(0xf4,'phase'),
    (8,'secondary_angle'),(0xc,'slip_ratio'),(0xb4,'kinetic_value'),(0x64,'local_lateral'),
    (0x68,'local_vertical'),(0x6c,'local_longitudinal'))


def verify(executable):
    from unicorn import UC_HOOK_CODE
    o=DynoOracle(executable);cpu,reg=o.cpu,o.reg
    owner,config=o.inputs,o.inputs+0x3000
    events=[];stub=o.stub+0x400;cpu.mem_write(stub,b'\xd9\xee\xc2\x14\x00')
    def effect(cpu,address,size,user):
        stack=cpu.reg_read(reg.UC_X86_REG_ESP)
        ret,operation,amount,zero,one,quarter=struct.unpack('<IIfIff',cpu.mem_read(stack,24))
        if cpu.reg_read(reg.UC_X86_REG_ECX)!=owner+0xcc8 or operation not in (1,2) or zero!=0 or one!=1 or quarter!=.25:
            raise AssertionError('unexpected component event')
        events.append((operation,amount));cpu.reg_write(reg.UC_X86_REG_EIP,stub)
    cpu.hook_add(UC_HOOK_CODE,effect,begin=0x591500,end=0x591500)
    count,maximum=0,0.0
    for s in cases():
        o._reset();events.clear()
        image=bytearray([0xa5])*0x1d00;data=bytearray([0x5a])*0x400
        struct.pack_into('<I',image,0x1c94,config);image[0xa69]=s.direction_mode;image[0xa88]=int(s.override_control)
        struct.pack_into('<i',image,0xab4,s.rpm);struct.pack_into('<f',image,0x1830+s.direction_mode*4,s.gear_multiplier)
        for off,name in OWNER_FIELDS:struct.pack_into('<f',image,off,getattr(s,name))
        for off,name in ((0x14c,'front_compliance'),(0x250,'rear_compliance'),(0x138,'front_secondary_angle'),(0x23c,'rear_secondary_angle')):
            struct.pack_into('<f',data,off,getattr(s,name))
        for i,w in enumerate(s.wheels):
            start=0x5fc+i*0x10c
            for off,name in WHEEL_FIELDS:struct.pack_into('<f',image,start+off,getattr(w,name))
            image[start+0xc5]=int(w.correction_enabled);image[start+0xec]=int(w.contact)
        cpu.mem_write(owner,bytes(image));cpu.mem_write(config,bytes(data))
        stack=o.frame-0x1000;cpu.mem_write(stack,struct.pack('<II',o.stop,owner));cpu.reg_write(reg.UC_X86_REG_ESP,stack)
        o._run(0x5400b0,o.stop,count=100000)
        actual=bytes(cpu.mem_read(owner,len(image)));expected=integrate_wheel_spin(s)
        for i,w in enumerate(expected.state.wheels):
            for off,name in WHEEL_FIELDS:
                if name not in ('spin_value','spin_scale','phase','secondary_angle','slip_ratio','kinetic_value','local_lateral','local_vertical','local_longitudinal'):continue
                pos=0x5fc+i*0x10c+off;value=struct.unpack_from('<f',actual,pos)[0];target=getattr(w,name);error=abs(value-target)
                if not math.isfinite(value) or error>max(.00025,abs(value)*3e-7):raise AssertionError((count,i,name,value,target,error,s))
                maximum=max(maximum,error);image[pos:pos+4]=actual[pos:pos+4]
        if actual!=image or bytes(cpu.mem_read(config,len(data)))!=data:raise AssertionError('unexpected state mutation')
        expected_events=tuple((1 if i<2 else 2,amount) for i,amount in expected.wear_events)
        if tuple(events)!=expected_events:raise AssertionError((count,events,expected_events))
        count+=1
    return {'cases':count,'maximum_absolute_error':maximum,'scope':'complete0x5400b0; component event delivery supplied; original event arguments checked'}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('executable')
    print(json.dumps(verify(p.parse_args().executable)))
