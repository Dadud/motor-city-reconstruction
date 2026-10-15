"""Compare six complete original engine component loaders, including rejection writes."""
import argparse
import json
import struct
from client.mechanical_loaders import MECHANICAL_LOADERS
from tools.mechanical_loaders_oracle import initial_configuration
from tools.native_oracle import DynoOracle


ENTRIES={1000001:0x54bd70,1100001:0x54bef0,1200001:0x54c090,
    180001:0x54bac0,190001:0x54bc10,200001:0x54b940}
BASE={1000001:(40.,(1.,1.,2.,1.,8.,40.,35.)),
    1100001:(12.,(1.,1.,1.,10.,10.,210.,220.,110.,110.)),
    1200001:(12.,(1.,1.,16.)),180001:(25.,(1.,.2)),
    190001:(.75,(1.,150.,.3)),200001:(.6,(1.,1.,.25,.4))}


def base_component(kind):
    mass,values=BASE[kind];part=bytearray(0x984)
    struct.pack_into('<I',part,0x14,len(values))
    struct.pack_into('<f',part,0x1c,1.25)
    struct.pack_into('<ff',part,0x30,mass,1.)
    struct.pack_into('<'+'f'*len(values),part,0x3c,*values)
    struct.pack_into('<I',part,0x53b,3)
    return part


def configuration(family=3,cylinders=8):
    image=bytearray(initial_configuration())
    struct.pack_into('<iI',image,0x43c,cylinders,family)
    struct.pack_into('<f',image,0x54,8.25)
    return bytes(image)


def cases():
    image=configuration()
    for kind in ENTRIES:
        original=base_component(kind)
        # Mutation boundaries, selector ties and exact float bounds.
        for offset in (0x30,0x34,*(0x3c+i*4 for i in range(len(BASE[kind][1])))):
            for value in (-1.,-.5,0.,.1,.5,.9,1.,1.1,1.5,2.,2.5,3.,3.5,4.,5.,6.,
                    7.5,7.9,8.,8.5,9.,9.5,10.,15.,20.,25.,25.4,30.,40.,50.,50.8,63.5,80.,150.,250.):
                part=bytearray(original);struct.pack_into('<f',part,offset,value)
                yield kind,image,bytes(part)
        for count in (0,1,2,3,4,7,9,0xc0000000|len(BASE[kind][1])):
            part=bytearray(original);struct.pack_into('<I',part,0x14,count)
            yield kind,image,bytes(part)
        for family in (0,1,3,26,27,0xffffffff):
            part=bytearray(original);struct.pack_into('<I',part,0x53b,family)
            for block_family in (0,1,3,26,27,0xffffffff):
                yield kind,configuration(block_family),bytes(part)
        if kind in (190001,200001):
            for cylinders in (6,7,8):
                for mass in (.10000000149,.60000002384,.79999995232,1.234567,1.99999988):
                    part=bytearray(original);struct.pack_into('<f',part,0x30,mass)
                    yield kind,configuration(cylinders=cylinders),bytes(part)


def verify(executable,database=None):
    records=list(cases());stock_count=0
    if database:
        from client.body_configuration import stock_body_configuration
        from client.catalogue import Catalogue
        from client.mechanical_parts import expand_mechanical_parts
        from tools.inspect_stock_mechanical import stock_slots,selected_parts
        catalogue=Catalogue.load(database);image=stock_body_configuration(catalogue,101).image
        for kind,part in selected_parts(expand_mechanical_parts(stock_slots(catalogue,101,percent_damage=0,item_wear=0))):
            if kind in ENTRIES:records.append((kind,image,part.image));stock_count+=1
            image=MECHANICAL_LOADERS[kind](image,part.image).configuration
    o=DynoOracle(executable);cpu=o.cpu;counts={};statuses={}
    for index,(kind,image,part) in enumerate(records):
        o._reset();target=o.inputs;source=o.inputs+0x1000
        cpu.mem_write(target,image);cpu.mem_write(source,part)
        stack=cpu.reg_read(o.reg.UC_X86_REG_ESP)
        cpu.mem_write(stack,struct.pack('<III',o.stop,target,source))
        o._run(ENTRIES[kind],o.stop,count=20000)
        expected=MECHANICAL_LOADERS[kind](image,part)
        actual=cpu.reg_read(o.reg.UC_X86_REG_EAX)
        if actual!=expected.status:raise AssertionError((index,kind,'status',actual,expected.status))
        for address,size,wanted in ((target,0x820,expected.configuration),(source,0x984,expected.component)):
            observed=bytes(cpu.mem_read(address,size))
            if observed!=wanted:
                offset=next(i for i,(a,b) in enumerate(zip(observed,wanted)) if a!=b)
                raise AssertionError((index,kind,hex(address),hex(offset),observed[offset:offset+4].hex(),wanted[offset:offset+4].hex()))
        counts[kind]=counts.get(kind,0)+1;key=f'{kind}:{actual}'
        statuses[key]=statuses.get(key,0)+1
    return dict(cases=len(records),by_type=counts,statuses=statuses,actual_stock_components=stock_count,
        maximum_absolute_error=0,scope='six complete original engine loaders with actual validators, family checks and CRT; all configuration/component bytes exact')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('executable');p.add_argument('--database')
    args=p.parse_args();print(json.dumps(verify(args.executable,args.database)))
