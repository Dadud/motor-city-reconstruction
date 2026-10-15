"""Original complete transmission, final drive, brake and suspension loaders."""
import argparse
import itertools
import json
import struct
from client.mechanical_loaders import MECHANICAL_LOADERS
from tools.native_oracle import DynoOracle


ENTRIES={130001:0x54d080,140001:0x54d2f0,100001:0x54d420,
    12001:0x54a840,11001:0x54a9a0,10001:0x54ab30}
BASE={130001:(30.,(0.,4.,8.,-2.5,0.,2.2,1.5,0.,0.,0.,0.,.8,1.,.9,.95,1.,1.,1.,1.)),
    140001:(22.5,(3.5,0.,.95)),100001:(12.,(1.,)),
    12001:(12.,(45000.,1.)),11001:(5.,(.3,.2032)),10001:(6.,(0.,1.,12.,.0508,0.))}


def base_component(kind,attachment=1,duty=1.):
    mass,values=BASE[kind];image=bytearray(0x984)
    struct.pack_into('<II',image,0x14,len(values),attachment)
    struct.pack_into('<ff',image,0x30,mass,duty)
    struct.pack_into('<'+'f'*len(values),image,0x3c,*values)
    struct.pack_into('<f',image,0x1c,1.25)
    return image


def cases():
    for kind,attachment,duty in itertools.product(ENTRIES,(0,1,2,3,4,5,10,11),
            (-.5,0.,.5,1.,1.5,2.,2.5,3.,3.5,4.)):
        yield kind,bytes(base_component(kind,attachment,duty))
    # Exercise every populated numeric field in isolation, including validation
    # refusals and selector round/truncate differences. Original function runs
    # make no service calls and all result bytes are checked.
    for kind in ENTRIES:
        original=base_component(kind)
        for offset in (0x14,0x30,*(0x3c+i*4 for i in range(len(BASE[kind][1])))):
            values=(0.,1.,2.,3.,3.9,4.,8.,8.9,9.,20.,100.,120000.)
            if offset==0x14:
                for count in (0,1,2,3,4,5,19,0xc0000000|len(BASE[kind][1])):
                    image=bytearray(original);struct.pack_into('<I',image,offset,count)
                    yield kind,bytes(image)
            else:
                for value in values:
                    image=bytearray(original);struct.pack_into('<f',image,offset,value)
                    yield kind,bytes(image)


def initial_configuration():
    image=bytearray(b'\xa5'*0x820)
    for offset,value in ((0x20,575.125),(0x28,25.5),(0x30,1.4224),(0x34,1.5132),
                         (0xfc,17.3),(0x104,28.7)):
        struct.pack_into('<f',image,offset,value)
    return bytes(image)


def verify(executable,database=None):
    o=DynoOracle(executable);cpu=o.cpu;counts={};statuses={}
    records=list(cases());actual_stock_count=0
    if database is not None:
        from client.catalogue import Catalogue
        from client.mechanical_parts import expand_mechanical_parts
        from tools.inspect_stock_mechanical import stock_slots,selected_parts
        catalogue=Catalogue.load(database)
        for kind,part in selected_parts(expand_mechanical_parts(stock_slots(catalogue,101,percent_damage=0,item_wear=0))):
            if kind in ENTRIES:
                records.append((kind,part.image));actual_stock_count+=1
    for kind,component in records:
        o._reset();target=o.inputs;source=o.inputs+0x1000
        image=initial_configuration()
        cpu.mem_write(target,image);cpu.mem_write(source,component)
        stack=cpu.reg_read(o.reg.UC_X86_REG_ESP)
        cpu.mem_write(stack,struct.pack('<III',o.stop,target,source))
        o._run(ENTRIES[kind],o.stop,count=20000)
        expected=MECHANICAL_LOADERS[kind](image,component)
        actual=cpu.reg_read(o.reg.UC_X86_REG_EAX)
        if actual!=expected.status:raise AssertionError((kind,counts.get(kind,0),'status',actual,expected.status))
        for address,size,wanted in ((target,0x820,expected.configuration),(source,0x984,expected.component)):
            observed=bytes(cpu.mem_read(address,size))
            if observed!=wanted:
                offset=next(i for i,(a,b) in enumerate(zip(observed,wanted)) if a!=b)
                raise AssertionError((kind,counts.get(kind,0),hex(address),hex(offset),observed[offset:offset+4].hex(),wanted[offset:offset+4].hex()))
        counts[kind]=counts.get(kind,0)+1;key=(kind,actual)
        statuses[str(key)]=statuses.get(str(key),0)+1
    return dict(cases=sum(counts.values()),by_type=counts,statuses=statuses,maximum_absolute_error=0,
        actual_vehicle_101_components=actual_stock_count,
        scope='six complete original component loaders with actual validators and CRT conversions; all configuration/component bytes exact; authored record corpus')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('executable');p.add_argument('--database')
    args=p.parse_args();print(json.dumps(verify(args.executable,args.database)))
