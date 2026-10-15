"""Isolate original curve-finalization branches using authored core outputs.

Only the cylinder solver is substituted. Full live-solver stock comparisons are
provided separately by engine_curve_oracle; neither proves runtime driving.
"""
import argparse
import json
from pathlib import Path
import struct
from client.catalogue import Catalogue
from client.dyno import load_flow_templates
from client.engine_curve import finalize_engine_configuration
from tools.engine_curve_oracle import loaded_engine
from tools.native_oracle import DynoOracle


def authored_core(record,minimum=8):
    out=bytearray(record)
    struct.pack_into('<19f',out,0x110,*(300+12*k-1.1*k*k for k in range(19)))
    struct.pack_into('<19f',out,0x15c,*(10+abs(k-minimum) for k in range(19)))
    struct.pack_into('<19f',out,0x1a8,*(.7+.01*k for k in range(19)))
    return bytes(out)


def cases(base):
    yield 'baseline',base,8
    for offset,kind,values in (
        (0x54,'f',(2.,4.,5.9,6.,10.)),
        (0x3cc,'f',(100.,299.,300.,600.,1600.)),
        (0x4cc,'i',(3000,6499,6500,12000)),
        (0x4d0,'f',(1.,100.,2000.)),
        (0x570,'i',(3500,6000,7000,12000)),
        (0x59c,'f',(0.,.01,5.,100.))):
        for value in values:
            image=bytearray(base);struct.pack_into('<'+kind,image,offset,value)
            yield f'{offset:x}:{value}',bytes(image),8
    for rpm in (3000,12000):
        for power in (1.,2000.):
            image=bytearray(base);struct.pack_into('<i',image,0x4cc,rpm)
            struct.pack_into('<f',image,0x4d0,power)
            yield f'electrical:{rpm}:{power}',bytes(image),8
    for minimum in (0,1,5,12,18):yield f'pressure:{minimum}',base,minimum


def verify(executable,database):
    from unicorn import UC_HOOK_CODE
    o=DynoOracle(executable);cpu=o.cpu;templates=load_flow_templates(executable)
    base=loaded_engine(Catalogue.load(database),101);total=0;reruns=0
    for label,image,minimum in cases(base):
        expected_calls=[];actual_calls=[]
        def solve(record):
            expected_calls.append(record)
            return authored_core(record,minimum)
        expected=finalize_engine_configuration(image,templates,engine_components_loaded=True,solver=solve)
        def replace(uc,address,size,data):
            stack=uc.reg_read(o.reg.UC_X86_REG_ESP)
            ret,record=struct.unpack('<II',uc.mem_read(stack,8))
            incoming=bytes(uc.mem_read(record,1004));actual_calls.append(incoming)
            uc.mem_write(record,authored_core(incoming,minimum))
            uc.reg_write(o.reg.UC_X86_REG_ESP,stack+4)
            uc.reg_write(o.reg.UC_X86_REG_EIP,ret)
        hook=cpu.hook_add(UC_HOOK_CODE,replace,begin=0x478ec0,end=0x478ec0)
        try:
            o._reset();cpu.mem_write(0x72000000,bytes(0x10000))
            cpu.mem_write(o.inputs,image);stack=cpu.reg_read(o.reg.UC_X86_REG_ESP)
            cpu.mem_write(stack,struct.pack('<II',o.stop,o.inputs))
            o._run(0x46d1d0,o.stop,count=1000000)
            actual=bytes(cpu.mem_read(o.inputs,0x820))
        finally:cpu.hook_del(hook)
        if actual_calls!=expected_calls:raise AssertionError((label,'solver input records'))
        if actual!=expected:
            offset=next(i for i,(a,b) in enumerate(zip(actual,expected)) if a!=b)
            raise AssertionError((label,hex(offset),actual[offset:offset+4].hex(),expected[offset:offset+4].hex()))
        total+=1;reruns+=len(actual_calls)>1
    return dict(cases=total,capacity_rerun_cases=reruns,maximum_absolute_error=0,
        substituted_calls=['0x478ec0 cylinder solver: authored outputs'],
        scope='whole configuration and every solver input record exact; curve correction and limit branches',
        original_runtime_driving_tested=False)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('executable',type=Path)
    p.add_argument('database',type=Path);a=p.parse_args()
    print(json.dumps(verify(a.executable,a.database)))
