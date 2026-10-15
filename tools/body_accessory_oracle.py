"""Full original body and stock accessory loaders; no substituted validators."""
import argparse
import json
import struct
from client.mechanical_loaders import MECHANICAL_LOADERS
from tools.native_oracle import DynoOracle
from tools.mechanical_loaders_oracle import initial_configuration

ENTRIES={20001:0x54a2b0,22001:0x54dd80,23001:0x54d740,
    31001:0x54de10,34001:0x54df90,35001:0x54dcb0,40001:0x54e060,
    13001:0x54cce0,14001:0x54cea0}


def base_component(kind):
    part=bytearray(0x984);counts={20001:39,22001:0,23001:1,31001:2,34001:1,35001:1,40001:2,13001:1,14001:0}
    struct.pack_into('<I',part,0x14,counts[kind]);struct.pack_into('<ff',part,0x30,10.,1.)
    struct.pack_into('<f',part,0x1c,1.25)
    if kind==20001:
        for offset,value in ((0x30,575.),(0x5c,1200.),(0x78,.35),
            (0x40,2.7),(0x44,1.4),(0x48,1.4),(0x4c,.5),(0x50,.4),
            (0x94,6.),(0x98,20.),(0x9c,20.),(0xa0,500.),(0xa4,500.),
            (0xb0,.3),(0xb4,.2),(0xb8,.2),(0xc4,10.),(0xc8,40.)):
            struct.pack_into('<f',part,offset,value)
    else:struct.pack_into('<ff',part,0x3c,100. if kind==13001 else .02,2.)
    if kind in (13001,14001):struct.pack_into('<I',part,0x18,10)
    return part


def cases():
    image=initial_configuration()
    for kind in ENTRIES:
        for offset in (0x30,0x34,*(range(0x3c,0xd8,4) if kind==20001 else (0x3c,0x40))):
            for value in (-5.,-.5,0.,.25,.5,1.,1.5,2.,3.,6.,6.5,9.,20.,400.,575.,1200.,6000.):
                part=base_component(kind);struct.pack_into('<f',part,offset,value)
                yield kind,image,bytes(part)
        for count in (0,1,2,39,0xc0000027):
            part=base_component(kind);struct.pack_into('<I',part,0x14,count)
            yield kind,image,bytes(part)
    for material in range(10):
        part=base_component(20001);struct.pack_into('<f',part,0xbc,material)
        yield 20001,image,bytes(part)
    for style in (0.,6.,6.9):
        for height in (.25399,.254,.30479,.3048,1.27,1.27001,1.5239999,1.5241):
            part=base_component(20001);struct.pack_into('<f',part,0x54,style)
            struct.pack_into('<f',part,0x4c,height)
            yield 20001,image,bytes(part)
    for text in (b'',b'part',b'a'*31):
        part=base_component(22001);part[0x120:0x120+len(text)]=text
        yield 22001,image,bytes(part)
    for kind in (13001,14001):
        for attachment in (0,1,4,10,11,12):
            for flags in (0,1):
                for wear in (0,1,2):
                    part=base_component(kind);struct.pack_into('<I',part,0x18,attachment)
                    for offset in (0x96c,0x930,0x51b):struct.pack_into('<I',part,offset,flags)
                    struct.pack_into('<I',part,0x527,wear);struct.pack_into('<I',part,0x94c,1)
                    yield kind,image,bytes(part)


def verify(executable,database=None):
    records=list(cases());actual=0
    if database:
        from client.catalogue import Catalogue
        from client.mechanical_parts import expand_mechanical_parts
        from tools.inspect_stock_mechanical import stock_slots
        for part in expand_mechanical_parts(stock_slots(Catalogue.load(database),101,percent_damage=0,item_wear=0)):
            kind=struct.unpack_from('<I',part.image,0x338)[0]
            if kind in ENTRIES:records.append((kind,initial_configuration(),part.image));actual+=1
    o=DynoOracle(executable);counts={}
    for index,(kind,image,part) in enumerate(records):
        o._reset();o.cpu.mem_write(o.inputs,image);o.cpu.mem_write(o.inputs+0x1000,part)
        stack=o.cpu.reg_read(o.reg.UC_X86_REG_ESP)
        o.cpu.mem_write(stack,struct.pack('<III',o.stop,o.inputs,o.inputs+0x1000))
        o._run(ENTRIES[kind],o.stop,count=100000)
        wanted=MECHANICAL_LOADERS[kind](image,part)
        status=o.cpu.reg_read(o.reg.UC_X86_REG_EAX)
        if status!=wanted.status:raise AssertionError((index,kind,'status',status,wanted.status))
        for address,size,expected in ((o.inputs,0x820,wanted.configuration),(o.inputs+0x1000,0x984,wanted.component)):
            observed=bytes(o.cpu.mem_read(address,size))
            if observed!=expected:
                offset=next(k for k,(a,b) in enumerate(zip(observed,expected)) if a!=b)
                raise AssertionError((index,kind,hex(offset),observed[offset:offset+4].hex(),expected[offset:offset+4].hex()))
        counts[kind]=counts.get(kind,0)+1
    return dict(cases=len(records),actual_stock_components=actual,by_type=counts,
        maximum_absolute_error=0,scope='complete original body, six accessory and two axle-bar loaders; full images/status exact')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('executable');p.add_argument('--database')
    a=p.parse_args();print(json.dumps(verify(a.executable,a.database)))
