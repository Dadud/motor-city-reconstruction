"""Original complete gear helper and enclosing numeric table producer.

No game entrypoint or host services run; finalized configuration is explicit.
"""
import argparse
import itertools
import json
import struct
from client.gear_binding import bind_gear_tables
from tools.native_oracle import DynoOracle


def cases():
    for rpm,tire,final,count in itertools.product((0,249,251,7000,9001),
            ((205,75,15),(300,30,20),(0,0,0)),(0.,3.5,-2.7),(0,1,2,4,8)):
        ratios=(2.5,0,2.2,1.7,1.3,1.,.8,.7)[:count]
        losses=(.8,1,.7,.9,.8,.9,.9,.9)[:count]
        yield rpm,*tire,ratios,losses,final


def verify(executable):
    o=DynoOracle(executable);count=0;cpu=o.cpu;config=o.inputs+0x3000
    for args in cases():
        rpm,width,aspect,rim,ratios,losses,final=args
        o._reset();image=bytearray(b'\xa5'*0x820)
        for off,value in ((0x70,rpm),(0x32c,len(ratios))):struct.pack_into('<i',image,off,value)
        for off,value in ((0x228,width),(0x22c,aspect),(0x230,rim),(0x374,final)):
            struct.pack_into('<f',image,off,value)
        for off,values in ((0x334,ratios),(0x354,losses)):
            struct.pack_into('<'+'f'*len(values),image,off,*values)
        cpu.mem_write(config,bytes(image));cpu.reg_write(o.reg.UC_X86_REG_ESI,config)
        # Start at the helper call setup; retain its real prologue and body.
        cpu.mem_write(o.frame-0x4d8,bytes(0xc8))
        cpu.reg_write(o.reg.UC_X86_REG_EAX,o.frame-0x4b4)
        o._run(0x53a536,0x53a5f6,count=10000)
        result=bind_gear_tables(*args)
        targets=((0x4b4,result.rpm_per_speed),(0x494,result.speed_per_rpm),
            (0x474,result.loss_final_ratio),(0x454,result.wheel_inertia_factors),
            (0x4d4,result.inverse_near_limit_speed),(0x414,(result.final_drive_inertia,)))
        for offset,values in targets:
            actual=bytes(cpu.mem_read(o.frame-offset,len(values)*4))
            expected=struct.pack('<'+'f'*len(values),*values)
            if actual!=expected:raise AssertionError((count,hex(offset),struct.unpack('<'+'f'*len(values),actual),values,args))
        if bytes(cpu.mem_read(config,len(image)))!=image:raise AssertionError('configuration changed')
        count+=1
    return dict(cases=count,maximum_absolute_error=0,
        scope='complete original 0x539fe0 and 0x53a536..0x53a5f6; exact six table/scalar outputs; supplied finalized configuration; no complete stock startup')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('executable')
    print(json.dumps(verify(p.parse_args().executable)))
