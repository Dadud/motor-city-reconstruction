"""Complete engine block loader, including original validation and quality."""
import argparse
import itertools
import json
import struct
from client.mechanical_loaders import load_engine_block
from tools.native_oracle import DynoOracle


def cases():
    for material,cylinders,count,family in itertools.product(
            (-.5,0.,.5,1.,2.,3.,3.9,4.,7.9,8.,8.9,9.,9.5),
            (5.5,6.,6.5,7.5,8.,8.5),(7,0xc0000007,6),(0,1,10,26,27)):
        component=bytearray(0x984)
        struct.pack_into('<I',component,0x14,count)
        struct.pack_into('<f',component,0x30,75)
        struct.pack_into('<f',component,0x34,2.7)
        struct.pack_into('<7f',component,0x3c,.08255,.09525,3.76,cylinders,2,material,25.)
        struct.pack_into('<I',component,0x53b,family)
        for i in range(6):
            text=(b'0' if i==0 else bytes([65+i]))+b'\0'
            component[0x120+i*32:0x122+i*32]=text
        yield bytes(component)
    # Validate all float range ends and adjacent representable float32 values.
    base=bytearray(next(cases_base()))
    for offset,low,high in ((0x30,30.,200.),(0x3c,.0508,.127),
            (0x40,.0635,.127),(0x44,3.,10.),(0x54,5.,40.)):
        for boundary in (low,high):
            bits=struct.unpack('<I',struct.pack('<f',boundary))[0]
            for shift in (-1,0,1):
                component=bytearray(base);struct.pack_into('<I',component,offset,bits+shift)
                yield bytes(component)


def cases_base():
    component=bytearray(0x984)
    struct.pack_into('<I',component,0x14,7);struct.pack_into('<I',component,0x53b,1)
    struct.pack_into('<f',component,0x30,75);struct.pack_into('<f',component,0x34,2)
    struct.pack_into('<7f',component,0x3c,.08255,.09525,3.76,8,2,0,25)
    yield bytes(component)


def verify(executable,database=None):
    o=DynoOracle(executable);cpu=o.cpu;count=0;statuses={0:0,1:0,2:0}
    records=list(cases());actual_stock_count=0
    if database is not None:
        from client.catalogue import Catalogue
        from client.mechanical_parts import expand_mechanical_parts
        from tools.inspect_stock_mechanical import stock_slots
        for part in expand_mechanical_parts(stock_slots(Catalogue.load(database),101,percent_damage=0,item_wear=0)):
            if struct.unpack_from('<I',part.image,0x338)[0]==160001:
                records.append(part.image);actual_stock_count+=1
    for component in records:
        o._reset();target=o.inputs;source=o.inputs+0x1000
        initial=bytearray(b'\xa5'*0x820);struct.pack_into('<f',initial,0x20,575.)
        cpu.mem_write(target,bytes(initial));cpu.mem_write(source,component)
        stack=cpu.reg_read(o.reg.UC_X86_REG_ESP)
        cpu.mem_write(stack,struct.pack('<III',o.stop,target,source))
        o._run(0x54a5a0,o.stop,count=20000)
        expected=load_engine_block(initial,component)
        actual=cpu.reg_read(o.reg.UC_X86_REG_EAX)
        if actual!=expected.status:raise AssertionError((count,'status',actual,expected.status))
        for address,size,wanted in ((target,0x820,expected.configuration),(source,0x984,expected.component)):
            observed=bytes(cpu.mem_read(address,size))
            if observed!=wanted:
                offset=next(i for i,(a,b) in enumerate(zip(observed,wanted)) if a!=b)
                raise AssertionError((count,hex(address),hex(offset),observed[offset:offset+4].hex(),wanted[offset:offset+4].hex()))
        statuses[actual]+=1;count+=1
    return dict(cases=count,statuses=statuses,maximum_absolute_error=0,actual_vehicle_101_components=actual_stock_count,
        scope='complete 0x54a5a0 including actual 0x542ef0 and CRT conversion; all configuration/component bytes exact; synthetic inputs, no complete stock assembly')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('executable');p.add_argument('--database')
    args=p.parse_args();print(json.dumps(verify(args.executable,args.database)))
