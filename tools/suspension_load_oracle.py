"""Complete original suspension/load correction with real sine helpers."""
import argparse
import itertools
import json
import struct
from client.suspension_load_correction import SuspensionLoadInput, correct_suspension_load
from tools.native_oracle import DynoOracle


def cases():
    for mask, attitude, speed, mode, disable, torque in itertools.product(range(16),
            (0, 0.25, 0.25001), (6, 6.001, -20), (0, 1), (False,True), (-500,0,500)):
        yield SuspensionLoadInput((1200,1600,900,1100), tuple(bool(mask & (1<<i)) for i in range(4)),
            attitude, True, speed, 0.08, -0.06, 1450, 100, 0.45, 0.55,
            1.2, 1.5, 2.7, 1.7, -2.3, torque, mode, disable)
    for enabled in (False, True):
        yield SuspensionLoadInput((1,2,3,4),(True,)*4,0,enabled,20,-0.1,0.1,
            1450,100,0.45,0.55,1.2,1.5,2.7,1.7,4,2000,0,False)


def verify(executable):
    o=DynoOracle(executable)
    cpu,reg=o.cpu,o.reg
    owner,config=o.inputs,o.inputs+0x3000
    offsets=(0x6d0,0x7dc,0x9f4,0x8e8)
    count,maximum=0,0.0
    for s in cases():
        o._reset()
        image=bytearray([0xa5])*0x1d00
        struct.pack_into('<I',image,0x1c94,config)
        struct.pack_into('<I',image,0xc08,int(s.enabled))
        struct.pack_into('<I',image,0x474,2 if s.disable_torque else 0)
        image[0xa69]=3
        values=list(zip(offsets,s.loads))+[(0xc00,s.attitude),(0xa2c,s.speed),(0xbf8,s.bank_angle),
            (0xbf4,s.pitch_angle),(0x18b8,s.front_lever),(0x18bc,s.rear_lever),(0xaa0,s.torque)]
        for offset,value in values:
            struct.pack_into('<f',image,offset,value)
        for offset,flag in zip((0x6e8,0x7f4,0xa0c,0x900),s.support):
            image[offset]=int(flag)
        cpu.mem_write(owner,bytes(image))
        configuration=bytearray([0x5a])*0x700
        struct.pack_into('<i',configuration,0x6ec,s.component_mode)
        for offset,value in ((0x20,s.mass),(0x28,s.mass_offset),(0x104,s.front_weight_parameter),
            (0xfc,s.rear_weight_parameter),(0x2c,s.wheelbase),(0x34,s.rear_track),
            (0x340,s.gear_factor)):
            struct.pack_into('<f',configuration,offset,value)
        cpu.mem_write(config,bytes(configuration))
        stack=o.frame-0x1000
        cpu.mem_write(stack,struct.pack('<II',o.stop,owner))
        cpu.reg_write(reg.UC_X86_REG_ESP,stack)
        o._run(0x53e980,o.stop,count=20000)
        actual=bytes(cpu.mem_read(owner,len(image)))
        for offset,target in zip(offsets,correct_suspension_load(s)):
            value=struct.unpack_from('<f',actual,offset)[0]
            error=abs(value-target)
            if error > max(0.00025,abs(value)*3e-7):
                raise AssertionError((count,s,hex(offset),value,target,error))
            maximum=max(maximum,error)
            image[offset:offset+4]=actual[offset:offset+4]
        if actual != image or cpu.mem_read(config,len(configuration)) != configuration:
            raise AssertionError('unexpected owner/configuration mutation')
        count+=1
    return {'cases':count,'maximum_absolute_error':maximum,
            'scope':'complete 0x53e980, original sine helpers, no substituted calls, synthetic isolated state'}


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('executable')
    print(json.dumps(verify(p.parse_args().executable)))
