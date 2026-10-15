"""Complete original intake, exhaust, cooling, electrical and lubrication loaders."""
import argparse
import itertools
import json
import struct
from client.mechanical_loaders import MECHANICAL_LOADERS
from tools.engine_component_loaders_oracle import configuration
from tools.native_oracle import DynoOracle

ENTRIES={320001:0x54af40,330001:0x54b0a0,340001:0x54b360,
    280001:0x54c710,290001:0x54c860,300001:0x54ca90,
    230001:0x54c440,240001:0x54c550,250001:0x54c340}
BASE={320001:(20.,(1.,1.,1.,2.)),330001:(5.,(1.,1.,600.)),
    340001:(5.,()),280001:(20.,(1.,1.,1.)),290001:(6.,(1.,0.,5.)),
    300001:(8.,(1.,1.)),230001:(30.,(25.,.05,.08,125.)),
    240001:(20.,(9000.,1000.)),250001:(12.,(10.,.00075))}


def base_component(kind):
    mass,values=BASE[kind];part=bytearray(0x984)
    struct.pack_into('<I',part,0x14,len(values));struct.pack_into('<f',part,0x1c,1.25)
    struct.pack_into('<ff',part,0x30,mass,1.)
    struct.pack_into('<'+'f'*len(values),part,0x3c,*values)
    struct.pack_into('<I',part,0x53b,3)
    return part


def cases():
    image=bytearray(configuration());struct.pack_into('<i',image,0x57c,1);image=bytes(image)
    for kind in ENTRIES:
        for offset in (0x30,0x34,*(0x3c+i*4 for i in range(len(BASE[kind][1])))):
            for value in (-1.,-.5,0.,.0005,.00075,.001,.01,.05,.1,.2,.5,.9,1.,1.1,
                    1.5,2.,2.5,3.,3.5,4.,5.,6.,7.5,7.9,8.,8.5,9.,9.5,10.,15.,20.,
                    25.,30.,50.,100.,125.,150.,600.,1000.,1600.,2000.,7000.,9999.5,12000.):
                part=base_component(kind);struct.pack_into('<f',part,offset,value)
                yield kind,image,bytes(part)
        for count in (0,1,2,3,4,7,9,0xc0000000|len(BASE[kind][1])):
            part=base_component(kind);struct.pack_into('<I',part,0x14,count)
            yield kind,image,bytes(part)
    for kind in (320001,280001):
        for family,block in itertools.product((0,1,3,26,27,0xffffffff),repeat=2):
            part=base_component(kind);struct.pack_into('<I',part,0x53b,family)
            yield kind,configuration(block),bytes(part)
    for flags in itertools.product((0,1),repeat=3):
        for source_wear,threshold in ((0,1),(1,0),(1,1),(2,1),(0xffffffff,0xfffffffe)):
            part=base_component(340001)
            for offset,value in zip((0x96c,0x930,0x51b),flags):struct.pack_into('<I',part,offset,value)
            struct.pack_into('<I',part,0x527,source_wear);struct.pack_into('<I',part,0x94c,threshold)
            yield 340001,image,bytes(part)
    for manifold,muffler in itertools.product((-1,0,1,2,3,4),(0.,.5,1.,1.5)):
        c=bytearray(image);struct.pack_into('<i',c,0x57c,manifold)
        part=base_component(300001);struct.pack_into('<f',part,0x40,muffler)
        yield 300001,bytes(c),bytes(part)
    for mass,flag,contribution in itertools.product((0.,6.,20.),(-1.,0.,.49,.5,1.,2.),(-1.,0.,5.,20.)):
        part=base_component(290001);struct.pack_into('<f',part,0x30,mass)
        struct.pack_into('<ff',part,0x40,flag,contribution)
        yield 290001,image,bytes(part)


def verify(executable,database=None):
    records=list(cases());actual=0
    if database:
        from client.body_configuration import stock_body_configuration
        from client.catalogue import Catalogue
        from client.mechanical_parts import expand_mechanical_parts
        from tools.inspect_stock_mechanical import stock_slots,selected_parts
        c=Catalogue.load(database);image=stock_body_configuration(c,101).image
        for kind,part in selected_parts(expand_mechanical_parts(stock_slots(c,101,percent_damage=0,item_wear=0))):
            if kind in ENTRIES:records.append((kind,image,part.image));actual+=1
            image=MECHANICAL_LOADERS[kind](image,part.image).configuration
    o=DynoOracle(executable);cpu=o.cpu;counts={};statuses={}
    for index,(kind,image,part) in enumerate(records):
        o._reset();target=o.inputs;source=target+0x1000
        cpu.mem_write(target,image);cpu.mem_write(source,part)
        stack=cpu.reg_read(o.reg.UC_X86_REG_ESP)
        cpu.mem_write(stack,struct.pack('<III',o.stop,target,source))
        o._run(ENTRIES[kind],o.stop,count=20000)
        expected=MECHANICAL_LOADERS[kind](image,part)
        status=cpu.reg_read(o.reg.UC_X86_REG_EAX)
        if status!=expected.status:raise AssertionError((index,kind,'status',status,expected.status))
        for address,size,wanted in ((target,0x820,expected.configuration),(source,0x984,expected.component)):
            observed=bytes(cpu.mem_read(address,size))
            if observed!=wanted:
                offset=next(i for i,(a,b) in enumerate(zip(observed,wanted)) if a!=b)
                raise AssertionError((index,kind,hex(offset),observed[offset:offset+4].hex(),wanted[offset:offset+4].hex()))
        counts[kind]=counts.get(kind,0)+1;key=f'{kind}:{status}'
        statuses[key]=statuses.get(key,0)+1
    return dict(cases=len(records),by_type=counts,statuses=statuses,actual_stock_components=actual,
        maximum_absolute_error=0,scope='nine complete original auxiliary loaders, actual validators and CRT; exact full configuration/component images')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('executable');p.add_argument('--database')
    a=p.parse_args();print(json.dumps(verify(a.executable,a.database)))
