"""Complete original 4c4050/4c42d0 calls and selected-node 52bc60 calls.

No child substitutions: 52bc60 executes its original CRT strstr. Synthetic owner
and linked nodes provide its established first-type0x11 selection input.
"""
import argparse
import json
import struct
from pathlib import Path
from client.model_preparation import part_half_extents,scale_part_streams,align_secondary_model
from tools.native_oracle import DynoOracle


def image(seed=0,alias=False,names=(b'body',b'part_W_detail',b'other_W')):
    b=bytearray([0x35])*0x2200
    struct.pack_into('<I',b,0x11c,3);struct.pack_into('<I',b,0x58,2)
    for stream,offset in ((0x14,0),(0x34,0 if alias else 0x60),(0x2c,0 if alias else 0xc0)):
        struct.pack_into('<I',b,stream,offset)
    for i in range(3):
        struct.pack_into('<I',b,0x420+i*4,i*2)
        struct.pack_into('<I',b,0x520+i*4,2 if i<2 else 0)
        struct.pack_into('<3f',b,0x120+i*12,seed+i*.1234567,-seed+i*.7654321,seed-i*1.234567)
        b[0xe28+i*64:0xe28+(i+1)*64]=names[i].ljust(64,b'\0')
    for i in range(2):struct.pack_into('<3f',b,0x5c+i*12,seed-i*2.345678,i*.3,-i*.6)
    for offset in (0,0x60,0xc0):
        for i in range(6):struct.pack_into('<3f',b,0x2038+offset+i*12,(-1)**i*(i+.1234567),i*.654321,seed-i*.7654321)
    return b


def cases():
    for seed in (0,1,-3,17.125):
        for alias in (False,True):
            for part in (-1,0,1,2,3):
                yield 'h',part,(1.,1.,1.),image(seed,alias),bytearray()
                yield 's',part,(-.9876543,.1234567,1.234567),image(seed,alias),bytearray()
        for names in ((b'body',b'part_W_detail',b'other_W'),(b'_w',b'none',b'none'),(b'_W',b'_W',b'_W')):
            for part in (0,2):yield 'a',part,(1.,1.,1.),image(seed,names=names),image(-seed)
    for part in (-1,-3):yield 'a',part,(1.,1.,1.),image(),image(4)


def expected(op,part,scales,b,ref):
    b=bytearray(b)
    if op=='h':
        v=part_half_extents(b,part)
        return int(v is not None),struct.pack('<3f',*v) if v else b''
    if op=='s':scale_part_streams(b,part,scales);return 0,bytes(b)
    changed=align_secondary_model(None if part==-1 else b,None if part==-2 else ref,None if part==-3 else part)
    return int(changed),bytes(b)


def verify(executable):
    o=DynoOracle(executable);c=o.cpu;base=0x73000000;c.mem_map(base,0x10000)
    count={'h':0,'s':0,'a':0}
    for op,part,scales,b,ref in cases():
        o._reset();c.mem_write(base,bytes(0x10000));c.mem_write(base,bytes(b))
        c.mem_write(base+0x4000,bytes(ref));c.mem_write(o.inputs,bytes([0x35])*12)
        stack=c.reg_read(o.reg.UC_X86_REG_ESP)
        status,wanted=expected(op,part,scales,b,ref)
        if op=='a':
            owner=base+0x8000;node=base+0x9000
            c.mem_write(owner+0x214,struct.pack('<I',0 if part==-1 else base))
            c.mem_write(owner+0x21c,struct.pack('<I',0 if part==-3 else node))
            c.mem_write(node,struct.pack('<II',0,base+0x4000))
            c.mem_write(node+0xc,struct.pack('<h',max(part,0)))
            c.mem_write(node+0x14,struct.pack('<I',0x11))
            c.reg_write(o.reg.UC_X86_REG_ECX,owner)
            args=struct.pack('<I',o.stop);entry=0x52bc60
        elif op=='h':args=struct.pack('<IIIi',o.stop,base,part&0xffffffff,o.inputs);entry=0x4c4050
        else:args=struct.pack('<IIi3f',o.stop,base,part,*scales);entry=0x4c42d0
        c.mem_write(stack,args);o._run(entry,o.stop)
        observed=bytes(c.mem_read(o.inputs,12)) if op=='h' and status else (b'' if op=='h' else bytes(c.mem_read(base,len(b))))
        if op=='h' and c.reg_read(o.reg.UC_X86_REG_EAX)!=status:raise AssertionError((op,part,'status'))
        if observed!=wanted:raise AssertionError((op,part,count[op],'memory mismatch'))
        count[op]+=1
    return {'calls':count,'maximum_absolute_error':0,'original_children_substituted':False,
            'full_model_startup_verified':False,'scope':'4c4050/4c42d0 complete bounded inputs;52bc60 selected-node alignment'}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('executable',type=Path)
    print(json.dumps(verify(p.parse_args().executable)))
