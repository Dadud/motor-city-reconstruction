"""Compare complete 0x53b260 with its real original torque lookup child."""
import argparse
import itertools
import json
import struct
from client.gear_force_table import gear_force_table
from tools.native_oracle import DynoOracle


def cases():
    for bounds,step,ratios in itertools.product(((0,12000),(800,6500),(1500,1500),(0,0)),
            (-100.,0.,.5,3.5,97.25,500.,15000.),((.1,.5),(1.,3.73),(5.,4.11))):
        config=bytearray(0x820)
        struct.pack_into('<ii',config,0x6c,*bounds)
        struct.pack_into('<26f',config,0x80,*(80.+i*13.37-(i%3)*70 for i in range(26)))
        geometry=((145.,80.,13.),(225.,60.,16.),(345.,30.,20.))[int(step)%3]
        for offset,value in ((0x228,geometry[0]),(0x22c,geometry[1]),(0x230,geometry[2]),(0x374,ratios[1])):
            struct.pack_into('<f',config,offset,value)
        for index in range(8):
            struct.pack_into('<f',config,0x334+index*4,ratios[0]*(index+1))
            struct.pack_into('<f',config,0x354+index*4,.65+index*.05)
        yield bytes(config),tuple(step+i*.125 if step>0 else step for i in range(8))


def verify(executable):
    o=DynoOracle(executable);cpu=o.cpu;count=0
    for config,steps in cases():
        for selector in range(8):
            expected=struct.pack('<135f',*gear_force_table(config,steps,selector))
            o._reset();cpu.mem_write(o.inputs,config);cpu.mem_write(o.inputs+0x1000,struct.pack('<8f',*steps))
            before=b'\xa5'*16;after=b'\x5a'*16;output=o.inputs+0x2000
            cpu.mem_write(output-16,before+b'\xcc'*(135*4)+after)
            stack=cpu.reg_read(o.reg.UC_X86_REG_ESP)
            cpu.mem_write(stack,struct.pack('<IIIII',o.stop,o.inputs,o.inputs+0x1000,selector,output))
            o._run(0x53b260,o.stop,count=200000)
            actual=bytes(cpu.mem_read(output-16,16+135*4+16))
            if actual!=before+expected+after:
                observed=struct.unpack('<135f',actual[16:-16]);wanted=struct.unpack('<135f',expected)
                raise AssertionError((count,selector,[(i,a,b) for i,(a,b) in enumerate(zip(observed,wanted)) if struct.pack('<f',a)!=struct.pack('<f',b)][:4]))
            if bytes(cpu.mem_read(o.inputs,len(config)))!=config:raise AssertionError('configuration changed')
            if bytes(cpu.mem_read(o.inputs+0x1000,32))!=struct.pack('<8f',*steps):raise AssertionError('RPM steps changed')
            count+=1
    return dict(calls=count,samples=count*135,maximum_absolute_error=0,real_original_child='0x548f00',
        output_sentinels_verified=True,configuration_unchanged=True,integrated_startup_verified=False)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('executable')
    print(json.dumps(verify(p.parse_args().executable)))
