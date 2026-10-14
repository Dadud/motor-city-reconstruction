"""Bounded original brake initialization/thermal range and complete helpers."""
import argparse
import itertools
import json
import struct

from client.brake_thermal import BrakeThermalAxle,BrakeThermalState,BrakeWorkWheel,update_brake_thermal
from tools.native_oracle import DynoOracle


def cases():
    for service,parking,speed,temperature,environment,code in itertools.product(
            (0,1),(False,True),(-10,-1,0,1,1.0001,10),(5,200,900),(False,True),(0,1,2)):
        front=BrakeThermalAxle(temperature,.25,1.1,450,8,400,2,1,2)
        rear=BrakeThermalAxle(temperature,.2,.9,430,6,350,3,0,0)
        wheels=tuple(BrakeWorkWheel((i-1)*300,.25+i*.1,(-1 if i%2 else 1)*(i+1)) for i in range(4))
        yield BrakeThermalState(front,rear,wheels,service,parking,speed,1500,10,environment,code)


def verify(executable):
    from unicorn import UC_HOOK_CODE
    o=DynoOracle(executable)
    control={}
    def query(cpu,address,size,user):
        stack=cpu.reg_read(o.reg.UC_X86_REG_ESP)
        ret=struct.unpack('<I',cpu.mem_read(stack,4))[0]
        cpu.reg_write(o.reg.UC_X86_REG_EAX,control['code'])
        cpu.reg_write(o.reg.UC_X86_REG_ESP,stack+4)
        cpu.reg_write(o.reg.UC_X86_REG_EIP,ret)
        control['calls']+=1
    o.cpu.hook_add(UC_HOOK_CODE,query,begin=0x594030,end=0x594030)
    count,maximum=0,0
    config=o.inputs+0x3000
    for state in cases():
        o._reset()
        image=bytearray([0xa5])*0x1d00
        data=bytearray([0xa5])*0x700
        struct.pack_into('<I',image,0x1c94,config)
        for offset,value in ((0xa90,state.service_control),(0xa2c,state.speed),(0x34c,state.elevation_parameter)):
            struct.pack_into('<f',image,offset,value)
        image[0xa6b]=int(state.parking_control)
        struct.pack_into('<I',image,0xae4,0)
        struct.pack_into('<f',data,0x20,state.mass_parameter)
        for axle,delta in ((state.front,0),(state.rear,0x20)):
            for offset,value in ((0xc7c+delta//8,axle.temperature),(0xc84+delta//8,axle.diameter),
                    (0xca4+delta//8,axle.cooling_coefficient),(0xcac+delta//8,axle.heat_capacity_factor)):
                struct.pack_into('<f',image,offset,value)
            struct.pack_into('<i',image,0xcb4+delta//8,axle.countdown)
            for offset,value in ((0x5c8+delta,axle.thermal_mass),(0x5e4+delta,axle.temperature_limit)):
                struct.pack_into('<f',data,offset,value)
            for offset,value in ((0x5d4+delta,axle.material_code),(0x5d0+delta,axle.construction_code)):
                struct.pack_into('<I',data,offset,value)
        for i,w in enumerate(state.wheels):
            base=0x5fc+i*0x10c
            for offset,value in ((0xbc,w.spin_scale),(0x7c,w.spin_value)):
                struct.pack_into('<f',image,base+offset,value)
            struct.pack_into('<f',image,0xc94+i*4,w.brake_force)
        o.cpu.mem_write(o.inputs,bytes(image));o.cpu.mem_write(config,bytes(data))
        o.cpu.mem_write(0x9aaa5c,struct.pack('<I',int(state.environment_flag)))
        control.update(code=state.environment_code,calls=0)
        stack=o.frame-0x1000
        o.cpu.mem_write(stack,struct.pack('<II',o.stop,o.inputs))
        o.cpu.reg_write(o.reg.UC_X86_REG_ESP,stack)
        o._run(0x538960,0x538ca4,count=20000)
        actual=bytes(o.cpu.mem_read(o.inputs,len(image)))
        expected=update_brake_thermal(state)
        for offset,value in ((0xc7c,expected.front.temperature),(0xc80,expected.rear.temperature),
                (0xcbc,expected.kinetic_value),(0xcc0,expected.elevation_value)):
            observed=struct.unpack_from('<f',actual,offset)[0];error=abs(observed-value)
            if error>max(.0001,abs(observed)*3e-7):raise AssertionError((count,offset,value,observed))
            maximum=max(maximum,error);image[offset:offset+4]=actual[offset:offset+4]
        for offset,value in ((0xcb4,expected.front.countdown),(0xcb8,expected.rear.countdown)):
            observed=struct.unpack_from('<i',actual,offset)[0]
            if observed!=value:raise AssertionError((count,offset,value,observed))
            image[offset:offset+4]=actual[offset:offset+4]
        for i in range(4):struct.pack_into('<f',image,0xc94+i*4,0)
        if actual!=image or bytes(o.cpu.mem_read(config,len(data)))!=data:raise AssertionError('unexpected mutation')
        if control['calls']!=1:raise AssertionError('environment query count mismatch')
        count+=1
    return {'cases':count,'maximum_absolute_error':maximum,
        'scope':'original538960 initialization/thermal stage only through538ca4; actual countdown/ambient helper; world query substituted'}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('executable')
    print(json.dumps(verify(p.parse_args().executable)))
