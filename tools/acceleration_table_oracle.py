"""Complete original acceleration producer/helper comparisons with real children."""
import argparse
import itertools
import json
import struct
from client.acceleration_table import acceleration_table,startup_force
from tools.native_oracle import DynoOracle


def cases():
    for mass,corrections,gate,second in itertools.product((650.,1400.,2600.),((0,0),(3,9),(30,50)),(0,1),(False,True)):
        c=bytearray(0x820);r=bytearray((i*37+11)%256 for i in range(0x4a8))
        struct.pack_into('<ii',c,0x6c,800,6500)
        struct.pack_into('<26f',c,0x80,*(25.+i*20.37-(i%3)*30 for i in range(26)))
        for offset,value in ((0x20,mass),(0x374,3.73),(0x6e8,.87),(0x3e0,1. if second else 0.),(0x3e4,1.)):
            struct.pack_into('<f',c,offset,value)
        for offset,value in ((0x4d8,corrections[0]),(0x4f4,corrections[1]),(0x68c,gate)):
            struct.pack_into('<i',c,offset,value)
        for i in range(8):
            struct.pack_into('<f',c,0x334+i*4,5.-i*.55)
            struct.pack_into('<f',r,0x64+i*4,.65+i*.04)
            struct.pack_into('<f',r,0x2c+i*4,200.-i*22.5)
            struct.pack_into('<f',r,0xac+i*4,(10,25,45,65,85,120,130,140)[i])
        struct.pack_into('<f',r,0x104,.326)
        yield bytes(c),bytes(r)


def helper_cases():
    records=list(cases())
    for index in (0,3,16,35):
        c,r=records[index]
        for rpm,selector,sample,secondary in itertools.product((1,800,1501,6500,12000),(0,2,7),(-1.,0.,.5,5.,10.,10.001),(False,True)):
            yield c,r,rpm,selector,sample,secondary


def verify(executable):
    o=DynoOracle(executable);cpu=o.cpu;producers=helpers=0
    cpu.mem_write(o.stub,b'\xdd\x1d'+struct.pack('<I',o.inputs+0x9000)+b'\xe9'+struct.pack('<i',o.stop-(o.stub+11)))
    for c,r,rpm,selector,sample,secondary in helper_cases():
        expected=struct.pack('<d',startup_force(c,r,rpm,selector,sample,secondary))
        o._reset();cpu.mem_write(o.inputs,c);cpu.mem_write(o.inputs+0x2000,r)
        stack=cpu.reg_read(o.reg.UC_X86_REG_ESP)
        cpu.mem_write(stack,struct.pack('<IIIIIfI',o.stub,o.inputs,o.inputs+0x2000,rpm,selector,sample,int(secondary)))
        o._run(0x538660,o.stop,count=50000)
        actual=bytes(cpu.mem_read(o.inputs+0x9000,8))
        if actual!=expected:raise AssertionError(('helper',helpers,rpm,selector,sample,secondary,struct.unpack('<d',actual)[0],struct.unpack('<d',expected)[0]))
        if bytes(cpu.mem_read(o.inputs,len(c)))!=c or bytes(cpu.mem_read(o.inputs+0x2000,len(r)))!=r:raise AssertionError('helper input mutation')
        helpers+=1
    for c,r in cases():
        expected=acceleration_table(c,r)
        o._reset();cpu.mem_write(o.inputs,c);cpu.mem_write(o.inputs+0x2000-16,b'\xa5'*16+r+b'\x5a'*16)
        stack=cpu.reg_read(o.reg.UC_X86_REG_ESP);cpu.mem_write(stack,struct.pack('<III',o.stop,o.inputs,o.inputs+0x2000))
        o._run(0x5384f0,o.stop,count=500000)
        actual=bytes(cpu.mem_read(o.inputs+0x2000-16,len(r)+32))
        if actual!=b'\xa5'*16+expected+b'\x5a'*16:
            a=struct.unpack('<298I',actual[16:-16]);b=struct.unpack('<298I',expected)
            raise AssertionError(('producer',producers,[(hex(i*4),x,y) for i,(x,y) in enumerate(zip(a,b)) if x!=y][:6]))
        if bytes(cpu.mem_read(o.inputs,len(c)))!=c:raise AssertionError('configuration mutation')
        producers+=1
    return dict(producer_calls=producers,helper_calls=helpers,producer_samples=producers*224,
        exact_output_bits=True,whole_record_and_sentinels_checked=True,real_original_children=True,
        integrated_startup_verified=False)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('executable');print(json.dumps(verify(p.parse_args().executable)))
