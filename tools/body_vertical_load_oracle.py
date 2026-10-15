"""Bounded original axle vertical-load comparison; no substituted helpers."""
import argparse
import itertools
import json
import math
import struct
from client.body_vertical_load import BodyVerticalLoadState, adjust_body_vertical_load
from tools.native_oracle import DynoOracle


def cases():
    for speed, velocity, parameter, adjustment, quality in itertools.product(
            (-20, 0, 8.94059, 8.9406, 8.94061, 30), (-3, 0, 3),
            (-2, 0, 2), (-.5, 0, .5), (0, .5, 1)):
        yield BodyVerticalLoadState(speed, velocity, parameter, -parameter, .3, -.4,
                                    adjustment, -adjustment, quality, 1-quality,
                                    (-100, 0, 200, 1000))


def verify(executable):
    o = DynoOracle(executable)
    owner, config = o.inputs, o.inputs+0x3000
    count, maximum = 0, 0.0
    for s in cases():
        o._reset()
        image, configuration = bytearray([0xa5])*0x1d00, bytearray([0x5a])*0x500
        struct.pack_into('<I', image, 0x1c94, config)
        for off, name in ((0xa2c,'speed'),(0xa44,'longitudinal_speed'),(0xd30,'front_adjustment'),
                          (0xd34,'rear_adjustment'),(0xd18,'front_quality'),(0xd1c,'rear_quality')):
            struct.pack_into('<f',image,off,getattr(s,name))
        for off,name in ((4,'front_parameter'),(8,'rear_parameter'),(0x410,'front_speed_parameter'),(0x420,'rear_speed_parameter')):
            struct.pack_into('<f',configuration,off,getattr(s,name))
        offsets=(0x6d0,0x7dc,0x8e8,0x9f4)
        for off,value in zip(offsets,s.wheel_loads): struct.pack_into('<f',image,off,value)
        o.cpu.mem_write(owner,bytes(image));o.cpu.mem_write(config,bytes(configuration))
        stack=o.frame-0x1000
        o.cpu.mem_write(stack,struct.pack('<II',o.stop,owner));o.cpu.reg_write(o.reg.UC_X86_REG_ESP,stack)
        o._run(0x536250,o.stop,count=20000)
        actual=bytes(o.cpu.mem_read(owner,len(image))); expected=adjust_body_vertical_load(s)
        values=(expected.front_vertical,expected.rear_vertical,expected.total_vertical,*expected.wheel_loads)
        for off,target in zip((0xbdc,0xbe0,0xbe4,*offsets),values):
            value=struct.unpack_from('<f',actual,off)[0];error=abs(value-target)
            if not math.isfinite(value) or error>max(.00025,abs(value)*3e-7):
                raise AssertionError((count,hex(off),value,target,s))
            maximum=max(maximum,error);image[off:off+4]=actual[off:off+4]
        if actual!=image or bytes(o.cpu.mem_read(config,len(configuration)))!=configuration:
            raise AssertionError('unexpected writes')
        count+=1
    return {'cases':count,'maximum_absolute_error':maximum,'scope':'complete0x536250 and0x536f80; no substitutions'}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('executable')
    print(json.dumps(verify(p.parse_args().executable)))
