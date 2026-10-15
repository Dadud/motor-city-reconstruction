"""Compare original auxiliary-table packing with substituted typed DB reads.

    Executes 0x67e520, not Jet/DAO. Allocator, query setup, typed column bindings,
    row fetches and cleanup are controlled substitutes. All returned table bytes
    except the process-specific allocation handle are checked.
"""
import argparse
import json
import struct
from client.tire_templates import (TIRE_QUERY_COLUMNS,build_tire_templates,
    read_tire_template_rows)
from tools.native_oracle import DynoOracle
from tools.tire_loader_oracle import template_rows


def verify(executable,database=None):
    from unicorn import UC_HOOK_CODE
    o=DynoOracle(executable);cpu=o.cpu;cpu.mem_map(0,0x1000)
    target=o.inputs;handle=o.inputs+0x1000;table=o.inputs+0x2000
    bindings=[];state={};calls={}
    cleanup={0x67f3f0:0,0x67fdd0:8,0x6804c0:8,0x67f890:0,
        0x65e910:0,0x65e870:0,0x67f5f0:12,0x67f640:12,0x67f610:16,
        0x67f700:4,0x6800b0:0,0x67f4a0:0}
    def hook(cpu,address,size,user):
        if address not in cleanup:return
        calls[address]=calls.get(address,0)+1
        stack=cpu.reg_read(o.reg.UC_X86_REG_ESP)
        def arg(index):return struct.unpack('<I',cpu.mem_read(stack+4+index*4,4))[0]
        value=0
        if address==0x65e910:
            if arg(0)!=0x1d68:raise AssertionError('unexpected auxiliary allocation')
            cpu.mem_write(handle,struct.pack('<I',table));value=handle
        elif address==0x67f890:value=len(state['rows'])
        elif address in (0x67f5f0,0x67f640,0x67f610):
            bindings.append((arg(0),arg(1),address))
        elif address==0x67f700:
            row=state['rows'][arg(0)]
            for ordinal,destination,operation in bindings:
                field=TIRE_QUERY_COLUMNS[ordinal]
                if operation==0x67f610:cpu.mem_write(destination,b'\0')
                else:cpu.mem_write(destination,struct.pack('<i' if operation==0x67f5f0 else '<f',row[field]))
        cpu.reg_write(o.reg.UC_X86_REG_EAX,value)
        cpu.reg_write(o.reg.UC_X86_REG_EIP,struct.unpack('<I',cpu.mem_read(stack,4))[0])
        cpu.reg_write(o.reg.UC_X86_REG_ESP,stack+4+cleanup[address])
    token=cpu.hook_add(UC_HOOK_CODE,hook)
    records=[template_rows(n) for n in (0,1,2,6,20)]
    if database:records.append(read_tire_template_rows(database))
    try:
        for rows in records:
            state['rows']=sorted(rows,key=lambda row:row['TireTypeID']);bindings.clear();o._reset()
            cpu.mem_write(table,b'\xa5'*0x1d68)
            stack=cpu.reg_read(o.reg.UC_X86_REG_ESP)
            cpu.mem_write(stack,struct.pack('<II',o.stop,target))
            o._run(0x67e520,o.stop,count=100000)
            pointer=struct.unpack('<I',cpu.mem_read(target,4))[0]
            if pointer!=table:raise AssertionError('auxiliary table pointer')
            expected=build_tire_templates(rows)
            actual=bytes(cpu.mem_read(table,0x1d68))
            if actual[4:]!=expected[4:]:
                offset=next(i for i,(a,b) in enumerate(zip(actual[4:],expected[4:]),4) if a!=b)
                raise AssertionError((len(rows),hex(offset),actual[offset:offset+4].hex(),expected[offset:offset+4].hex()))
    finally:cpu.hook_del(token)
    return dict(cases=len(records),record_counts=[len(r) for r in records],maximum_absolute_error=0,
        actual_database_rows=len(records[-1]) if database else 0,
        scope='original auxiliary allocation/clearing/bind/fetch/packing control flow with supplied allocator and typed database services; all bytes except allocation handle exact; Jet execution untested')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('executable');p.add_argument('--database')
    args=p.parse_args();print(json.dumps(verify(args.executable,args.database)))
