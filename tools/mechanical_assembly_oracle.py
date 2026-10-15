"""Complete original mechanical assembly with external stock parts and tables."""
import argparse
import json
from pathlib import Path
import struct
from client.catalogue import Catalogue
from client.dyno import load_flow_templates
from client.mechanical_assembly import assemble_mechanical_components
from client.mechanical_parts import expand_mechanical_parts
from client.tire_templates import load_tire_templates
from tools.inspect_stock_mechanical import stock_slots
from tools.native_oracle import DynoOracle


def stock_assembly(catalogue,vehicle,templates,tire_templates):
    parts=expand_mechanical_parts(stock_slots(catalogue,vehicle,percent_damage=0,item_wear=0))
    return assemble_mechanical_components(tuple(p.image for p in parts),templates,tire_templates=tire_templates)


def failure_scenarios(parts):
    def kind(p):return struct.unpack_from('<I',p,0x338)[0]
    for removed in (20001,160001,110001):
        yield f'missing:{removed}',tuple(p for p in parts if kind(p)!=removed)
    for target,offset,code,value in ((20001,0x14,'I',1),(160001,0x14,'I',1),
            (160001,0x30,'f',0.),(22001,0x30,'f',0.),(10001,0x30,'f',0.),
            (10001,0x18,'I',5)):
        index=next(i for i,p in enumerate(parts) if kind(p)==target)
        altered=bytearray(parts[index]);struct.pack_into('<'+code,altered,offset,value)
        changed=list(parts);changed[index]=bytes(altered)
        yield f'rejected:{target}:{offset:x}',tuple(changed)
    index=next(i for i,p in enumerate(parts) if kind(p)==160001)
    altered=bytearray(parts[index]);struct.pack_into('<I',altered,0x14,1)
    yield 'rejected_then_valid_duplicate',tuple([*parts[:index],bytes(altered),*parts[index:]])
    yield 'valid_duplicate_ignored',tuple([*parts,parts[index]])


def verify(executable,database,vehicles=(101,)):
    catalogue=Catalogue.load(database);templates=load_flow_templates(executable)
    tires=load_tire_templates(database);o=DynoOracle(executable);cpu=o.cpu
    base=0x73000000;stride=0x1000;cpu.mem_map(base,0x100000);reports=[]
    cpu.mem_write(o.inputs+0x2000,tires);cpu.mem_write(0xb299e8,struct.pack('<I',o.inputs+0x2000))
    scenarios=[]
    for vehicle in vehicles:
        parts=expand_mechanical_parts(stock_slots(catalogue,vehicle,percent_damage=0,item_wear=0))
        scenarios.append((str(vehicle),tuple(p.image for p in parts)))
        if vehicle==101:scenarios.extend(failure_scenarios(tuple(p.image for p in parts)))
    initial=bytes((k*13+7)&255 for k in range(0x820))
    for vehicle,parts in scenarios:
        if len(parts)>255:raise ValueError('oracle component limit')
        expected=assemble_mechanical_components(parts,templates,tire_templates=tires,initial_configuration=initial)
        if expected.unsupported:raise ValueError((vehicle,'unsupported',expected.unsupported))
        o._reset();cpu.mem_write(0x72000000,bytes(0x10000));cpu.mem_write(o.inputs,initial)
        for index,part in enumerate(parts):
            image=bytearray(part);struct.pack_into('<I',image,0,base+(index+1)*stride if index+1<len(parts) else 0)
            cpu.mem_write(base+index*stride,bytes(image))
        stack=cpu.reg_read(o.reg.UC_X86_REG_ESP)
        cpu.mem_write(stack,struct.pack('<III',o.stop,o.inputs,base if parts else 0))
        o._run(0x54e720,o.stop,timeout=20000000,count=150000000)
        status=cpu.reg_read(o.reg.UC_X86_REG_EAX)
        if status!=expected.status:raise AssertionError((vehicle,'status',status,expected.status))
        actual=bytes(cpu.mem_read(o.inputs,0x820))
        if actual!=expected.configuration:
            offset=next(k for k,(a,b) in enumerate(zip(actual,expected.configuration)) if a!=b)
            raise AssertionError((vehicle,'configuration',hex(offset),actual[offset:offset+4].hex(),expected.configuration[offset:offset+4].hex()))
        for index,wanted in enumerate(expected.components):
            observed=bytes(cpu.mem_read(base+index*stride,0x984))
            if observed[4:]!=wanted[4:]:
                offset=next(k for k in range(4,0x984) if observed[k]!=wanted[k])
                raise AssertionError((vehicle,'component',index,hex(offset),observed[offset:offset+4].hex(),wanted[offset:offset+4].hex()))
        reports.append(dict(scenario=vehicle,status=status,components=len(parts),loader_calls=len(expected.loader_calls),
            total_mass=struct.unpack_from('<f',actual,0x20)[0] if status else None,
            idle_rpm=struct.unpack_from('<i',actual,0x6c)[0] if status else None,
            maximum_rpm=struct.unpack_from('<i',actual,0x70)[0] if status else None))
    return dict(cases=len(reports),vehicles=reports,maximum_absolute_error=0,substituted_calls=[],
        scope='complete original 0x54e720 including all stock loader calls, quality updates, weight and engine finalizers; full config and component bytes except linked-list addresses',
        original_runtime_driving_tested=False)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('executable',type=Path)
    p.add_argument('database',type=Path);p.add_argument('--vehicles',type=int,nargs='+',default=[101])
    a=p.parse_args();print(json.dumps(verify(a.executable,a.database,a.vehicles)))
