"""Original tire loader against explicit auxiliary records, with full-image checks."""
import argparse
import json
import struct
from client.mechanical_loaders import load_tire
from client.tire_templates import build_tire_templates,load_tire_templates
from tools.mechanical_loaders_oracle import initial_configuration
from tools.native_oracle import DynoOracle


def template_rows(count=6):
    rows=[]
    for index in range(count):
        row=dict(TireTypeID=index,TireType=index%3,RainFlag=index%2,
            RollingResistFactor=.95+index*.001,GrowthFactor=5.+index,
            PeakFriction=.8+index*.01,CamberCoefficient=.02,SectionWidth=178.+index*10)
        row.update({f'Val{i+1}':i*.03125 for i in range(36)})
        row.update({f'LatForce{i+1}':(i+1)*100.+index for i in range(25)})
        row.update({f'AlignMom{i+1}':(i-12)*3.5+index for i in range(25)})
        rows.append(row)
    return rows


def base_component(attachment=1):
    part=bytearray(0x984);struct.pack_into('<II',part,0x14,4,attachment)
    struct.pack_into('<ff',part,0x30,12.5,1.)
    struct.pack_into('<4f',part,0x3c,205.,75.,15.,1.)
    struct.pack_into('<f',part,0x1c,1.25)
    return part


def cases():
    image=bytearray(initial_configuration());struct.pack_into('<f',image,0,.35)
    image=bytes(image);templates=build_tire_templates(template_rows())
    for attachment in (0,1,2,3,4,5,10,11):
        for width in (100.,205.,215.,215.00002,225.,339.9,340.,500.):
            for selector in (0.,1.,3.9,4.,4.5,5.,6.,19.):
                part=base_component(attachment);struct.pack_into('<f',part,0x3c,width)
                struct.pack_into('<f',part,0x48,selector)
                yield image,bytes(part),templates
    for offset in (0x30,0x34,0x3c,0x40,0x44):
        for value in (-1.,0.,.5,1.,1.5,2.,2.5,3.,3.5,4.,8.,12.,25.,30.,95.,100.,500.):
            part=base_component();struct.pack_into('<f',part,offset,value)
            yield image,bytes(part),templates
    for peak in (.69999,.7,1.,2.,2.00001):
        for section in (126.99,127.,508.,508.01):
            rows=template_rows();rows[1]['PeakFriction']=peak;rows[1]['SectionWidth']=section
            yield image,bytes(base_component()),build_tire_templates(rows)
    for count in (0,1,4,5,0xc0000004):
        part=base_component();struct.pack_into('<I',part,0x14,count)
        yield image,bytes(part),templates
        yield image,bytes(part),None


def verify(executable,database=None):
    records=list(cases());actual=0
    if database:
        from client.catalogue import Catalogue
        from client.mechanical_parts import expand_mechanical_parts
        from tools.inspect_stock_mechanical import stock_slots
        templates=load_tire_templates(database)
        catalogue=Catalogue.load(database)
        for part in expand_mechanical_parts(stock_slots(catalogue,101,percent_damage=0,item_wear=0)):
            if struct.unpack_from('<I',part.image,0x338)[0]==110001:
                records.append((records[0][0],part.image,templates));actual+=1
    o=DynoOracle(executable);cpu=o.cpu;statuses={}
    for index,(image,part,templates) in enumerate(records):
        o._reset();target=o.inputs;source=o.inputs+0x1000;table=o.inputs+0x2000
        cpu.mem_write(target,image);cpu.mem_write(source,part)
        cpu.mem_write(0xb299e8,struct.pack('<I',table if templates is not None else 3))
        if templates is not None:cpu.mem_write(table,templates)
        stack=cpu.reg_read(o.reg.UC_X86_REG_ESP)
        cpu.mem_write(stack,struct.pack('<III',o.stop,target,source))
        o._run(0x54e170,o.stop,count=20000)
        expected=load_tire(image,part,templates)
        status=cpu.reg_read(o.reg.UC_X86_REG_EAX)&255
        if status!=expected.status:raise AssertionError((index,'status',status,expected.status))
        for address,size,wanted in ((target,0x820,expected.configuration),(source,0x984,expected.component)):
            observed=bytes(cpu.mem_read(address,size))
            if observed!=wanted:
                offset=next(i for i,(a,b) in enumerate(zip(observed,wanted)) if a!=b)
                raise AssertionError((index,hex(offset),observed[offset:offset+4].hex(),wanted[offset:offset+4].hex()))
        statuses[status]=statuses.get(status,0)+1
    return dict(cases=len(records),statuses=statuses,actual_stock_components=actual,
        maximum_absolute_error=0,scope='complete original tire loader/accessor/validators with supplied auxiliary image; exact configuration/component bytes; no database service execution')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('executable');p.add_argument('--database')
    args=p.parse_args();print(json.dumps(verify(args.executable,args.database)))
