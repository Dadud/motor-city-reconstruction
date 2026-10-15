"""Original mechanical numeric transfer; geometry/display calls stay excluded."""
import argparse
import itertools
import json
import struct
from client.mechanical_parts import transfer_mechanical_physics
from tools.native_oracle import DynoOracle


def cases():
    for damage,wear,attachment in itertools.product((0,1,99,100,0x7fffffff,0xffffffff),
            (0,17,0x7fffffff,0xffffffff),(0,1,4,10,11)):
        slot=bytearray(1596)
        for offset,value in ((0x610,damage),(0x614,wear),(0x408,0x7fffffff),
                (0x40c,0xffffffff),(0x410,0x80000001),(0x418,17),(0x41c,371),
                (0x420,0xc0000032),(0x424,8),(0x428,0x12345678)):
            struct.pack_into('<I',slot,offset,value)
        struct.pack_into('<i',slot,0x1ef,-27)
        struct.pack_into('<f',slot,0x414,75.125)
        struct.pack_into('<50f',slot,0x42c,*(i*.125 for i in range(50)))
        for i in range(8):
            text=(b'' if i==1 else (f'slot-{i}'.encode()*4)[:31])+b'\0'
            slot[0x4f4+i*32:0x4f4+i*32+len(text)]=text
        yield bytes(slot),attachment


def verify(executable):
    o=DynoOracle(executable);cpu=o.cpu;count=0
    for slot,attachment in cases():
        o._reset();source=o.inputs;target=o.inputs+0x1000
        initial=b'\xa5'*0x984
        cpu.mem_write(source,slot);cpu.mem_write(target,initial)
        stack=cpu.reg_read(o.reg.UC_X86_REG_ESP)
        cpu.mem_write(stack,struct.pack('<IIIi',o.stop,target,source,attachment))
        o._run(0x52c2e0,0x52c37b,count=5000)
        # Jump over only the geometry filename/picture and display formatting
        # region. Its CPU register boundary is explicit, not claimed recovered.
        cpu.reg_write(o.reg.UC_X86_REG_ESI,0)
        o._run(0x52c466,0x52c542,count=5000)
        actual=bytes(cpu.mem_read(target,0x984))
        expected=transfer_mechanical_physics(slot,attachment,initial_image=initial)
        if actual!=expected:
            offset=next(i for i,(a,b) in enumerate(zip(actual,expected)) if a!=b)
            raise AssertionError((count,hex(offset),actual[offset:offset+4].hex(),expected[offset:offset+4].hex()))
        if bytes(cpu.mem_read(source,1596))!=slot:raise AssertionError('source changed')
        count+=1
    return dict(cases=count,maximum_absolute_error=0,
        scope='0x52c2e0..0x52c37b and 0x52c466..0x52c542; full mechanical image exact; geometry/display region skipped with explicit register handoff')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('executable')
    print(json.dumps(verify(p.parse_args().executable)))
