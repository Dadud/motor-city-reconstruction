"""Complete original angular accumulation and support-correction helper."""
import argparse
import itertools
import json
import math
import struct
from client.body_moments import BodyMomentState,MomentWheel,accumulate_body_moments
from tools.native_oracle import DynoOracle


def cases():
    for speed,force,correction,mask,alternate in itertools.product(
            (-20,.49999,.5,.50001,20),(-1000,0,1000),(-.2,0,.2),range(16),(False,True)):
        wheels=tuple(MomentWheel(force+i*37,force-i*71,(i-1)*19,correction*(i-1),bool(mask&(1<<i))) for i in range(4))
        yield BodyMomentState(wheels,speed,1.2,1.5,1.6,1.7,.7,1300,.003,.002,.004,.8,300,400,53,alternate)


def verify(executable):
    o=DynoOracle(executable);cpu,reg=o.cpu,o.reg
    owner,config=o.inputs,o.inputs+0x3000
    count,maximum=0,0.0
    for s in cases():
        o._reset()
        image=bytearray([0xa5])*0x1d00
        struct.pack_into('<I',image,0x1c94,config)
        for off,name in ((0xa2c,'speed'),(0x18b8,'front_lever'),(0x18bc,'rear_lever'),
            (0x18e0,'inverse_pitch'),(0x18e4,'inverse_yaw'),(0x18e8,'inverse_roll'),
            (0xc0c,'pitch_multiplier'),(0xbdc,'front_vertical'),(0xbe0,'rear_vertical'),(0xbcc,'yaw_contribution')):
            struct.pack_into('<f',image,off,getattr(s,name))
        for i,w in enumerate(s.wheels):
            for off,name in ((0xd0,'lateral_force'),(0xd8,'longitudinal_force'),(0xe0,'secondary_response'),(0x74,'support_correction')):
                struct.pack_into('<f',image,0x5fc+i*0x10c+off,getattr(w,name))
            image[0x6e8+i*0x10c]=int(w.contact)
        configuration=bytearray([0x5a])*0x100
        for off,name in ((0x20,'mass_parameter'),(0x30,'front_track'),(0x34,'rear_track'),(0x38,'height_parameter')):
            struct.pack_into('<f',configuration,off,getattr(s,name))
        cpu.mem_write(owner,bytes(image));cpu.mem_write(config,bytes(configuration))
        cpu.mem_write(0xa384c8,struct.pack('<I',int(s.alternate_mode)))
        stack=o.frame-0x1000;cpu.mem_write(stack,struct.pack('<II',o.stop,owner));cpu.reg_write(reg.UC_X86_REG_ESP,stack)
        o._run(0x540710,o.stop,count=20000)
        actual=bytes(cpu.mem_read(owner,len(image)))
        for off,target in zip((0xa48,0xa4c,0xa50),accumulate_body_moments(s)):
            value=struct.unpack_from('<f',actual,off)[0];error=abs(value-target)
            if not math.isfinite(value) or error>max(.00025,abs(value)*3e-7):
                raise AssertionError((count,hex(off),value,target,error,s))
            maximum=max(maximum,error);image[off:off+4]=actual[off:off+4]
        if actual!=image or bytes(cpu.mem_read(config,len(configuration)))!=configuration:
            raise AssertionError('unexpected state writes')
        count+=1
    return {'cases':count,'maximum_absolute_error':maximum,'scope':'complete 0x540710, original cross products and 0x540600; no substituted calls'}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('executable')
    print(json.dumps(verify(p.parse_args().executable)))
