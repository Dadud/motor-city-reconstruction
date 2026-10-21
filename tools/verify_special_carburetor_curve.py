"""Compare carburetor-six engine finalization against the installed original."""
import argparse
import json
from pathlib import Path
import struct
from unicorn import UC_HOOK_CODE
from client.catalogue import Catalogue
from client.dyno import load_flow_templates
from client.engine_curve import build_assembled_core_record,finalize_engine_configuration
from tools.engine_curve_oracle import loaded_engine
from tools.native_oracle import DynoOracle


def verify(executable,database,vehicles=(101,102,103,104,105,106,107,108)):
    catalogue=Catalogue.load(database);templates=load_flow_templates(executable)
    oracle=DynoOracle(executable);reports=[]
    cases=[(vehicle,None) for vehicle in vehicles]
    cases.extend((101,capacity) for capacity in (100.,300.,480.,1200.,2400.))
    for vehicle,capacity_override in cases:
        image=bytearray(loaded_engine(catalogue,vehicle))
        struct.pack_into('<i',image,0x3c8,6)
        if capacity_override is not None:
            struct.pack_into('<f',image,0x3cc,capacity_override)
        image=bytes(image)
        record=build_assembled_core_record(image,templates)
        if record!=oracle.builder_inputs(image):
            raise AssertionError((vehicle,'initial solver input differs'))
        authored_records=[]
        from client.cylinder_solver import solve_core_record
        def authored_solver(data):
            authored_records.append(data)
            return solve_core_record(data)
        expected=finalize_engine_configuration(image,templates,engine_components_loaded=True,
                                               solver=authored_solver)
        original_records=[]
        def capture(cpu,address,size,user_data):
            stack=cpu.reg_read(oracle.reg.UC_X86_REG_ESP)
            pointer=struct.unpack('<I',cpu.mem_read(stack+4,4))[0]
            original_records.append(bytes(cpu.mem_read(pointer,1004)))
        hook=oracle.cpu.hook_add(UC_HOOK_CODE,capture,begin=0x478ec0,end=0x478ec0)
        try:
            oracle._reset();oracle.cpu.mem_write(0x72000000,bytes(0x10000))
            oracle.cpu.mem_write(oracle.inputs,image)
            stack=oracle.cpu.reg_read(oracle.reg.UC_X86_REG_ESP)
            oracle.cpu.mem_write(stack,struct.pack('<II',oracle.stop,oracle.inputs))
            oracle._run(0x46d1d0,oracle.stop,timeout=10_000_000,count=100_000_000)
            actual=bytes(oracle.cpu.mem_read(oracle.inputs,0x820))
        finally:
            oracle.cpu.hook_del(hook)
        if actual!=expected:
            offset=next(i for i,(a,b) in enumerate(zip(actual,expected)) if a!=b)
            raise AssertionError((vehicle,'configuration',hex(offset),actual[offset:offset+4].hex(),expected[offset:offset+4].hex()))
        if len(original_records)!=2 or len(authored_records)!=2:
            raise AssertionError((vehicle,'expected two solver calls',len(original_records),len(authored_records)))
        for index,(original_input,authored_input) in enumerate(zip(original_records,authored_records)):
            if original_input!=authored_input:
                offset=next(i for i,(a,b) in enumerate(zip(original_input,authored_input)) if a!=b)
                raise AssertionError((vehicle,'solver input',index,hex(offset),original_input[offset:offset+4].hex(),authored_input[offset:offset+4].hex()))
        reports.append(dict(vehicle_id=vehicle,configured_capacity=struct.unpack_from('<f',image,0x3cc)[0],solver_calls=len(original_records),
            initial_capacity=struct.unpack_from('<h',original_records[0],0xa4)[0],
            rerun_capacity=struct.unpack_from('<h',original_records[1],0xa4)[0],
            idle_rpm=struct.unpack_from('<i',actual,0x6c)[0],
            maximum_rpm=struct.unpack_from('<i',actual,0x70)[0]))
    return dict(cases=len(reports),vehicles=reports,maximum_byte_error=0,
        scope='carburetor-six engine finalization: original builder, both live solver inputs and full configuration compared byte-for-byte; installed catalogue engines 101-108 plus five capacity variations on vehicle 101')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable',type=Path);parser.add_argument('database',type=Path)
    parser.add_argument('--vehicles',type=int,nargs='+',default=[101,102,103,104,105,106,107,108])
    args=parser.parse_args();print(json.dumps(verify(args.executable,args.database,args.vehicles),indent=2))
