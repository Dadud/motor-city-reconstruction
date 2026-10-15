"""Compare reconstructed stock engine finalization with complete original calls.

    Component selection is the recovered subset; this does not assert whole-car
    assembly. These cases execute the original solver. Authored-output branch
    isolation is provided separately by engine_curve_tail_oracle.
"""
import argparse
import json
from pathlib import Path
import struct
from client.body_configuration import stock_body_configuration
from client.catalogue import Catalogue
from client.dyno import load_flow_templates
from client.engine_curve import build_assembled_core_record,finalize_engine_configuration
from client.mechanical_loaders import MECHANICAL_LOADERS
from client.mechanical_parts import expand_mechanical_parts
from tools.inspect_stock_mechanical import selected_parts,stock_slots
from tools.native_oracle import DynoOracle


def loaded_engine(catalogue,vehicle):
    image=stock_body_configuration(catalogue,vehicle).image;seen=set()
    parts=expand_mechanical_parts(stock_slots(catalogue,vehicle,percent_damage=0,item_wear=0))
    for kind,part in selected_parts(parts):
        if kind==110001:continue
        result=MECHANICAL_LOADERS[kind](image,part.image)
        if result.status:raise ValueError(f'{vehicle}: loader {kind} status {result.status}')
        image=result.configuration;seen.add(kind)
    required={160001,1000001,1100001,180001,190001,200001,1200001,
        320001,330001,280001,230001,240001,250001}
    if not required<=seen:raise ValueError(f'{vehicle}: missing engine loaders {sorted(required-seen)}')
    # Extra engine families require their own verified loaders, not a zero-filled
    # approximation. Optional omitted mufflers use the original numeric fallback.
    if any(p.abstract_type_id in (150001,350001,360001,340333,310001) for p in catalogue.vehicle(vehicle).parts):
        raise ValueError(f'{vehicle}: unsupported additional engine component')
    if struct.unpack_from('<f',image,0x5a0)[0]<=0:
        kind=struct.unpack_from('<i',image,0x57c)[0]
        out=bytearray(image);struct.pack_into('<f',out,0x5b0,.025 if kind==0 else .03 if kind==1 else 0.)
        image=bytes(out)
    return image


def verify(executable,database,vehicles=(101,)):
    catalogue=Catalogue.load(database);templates=load_flow_templates(executable)
    o=DynoOracle(executable);cpu=o.cpu;reports=[]
    for vehicle in vehicles:
        image=loaded_engine(catalogue,vehicle)
        record=build_assembled_core_record(image,templates)
        if record!=o.builder_inputs(image):raise AssertionError((vehicle,'core builder image'))
        expected=finalize_engine_configuration(image,templates,engine_components_loaded=True)
        o._reset();cpu.mem_write(0x72000000,bytes(0x10000))
        cpu.mem_write(o.inputs,image);stack=cpu.reg_read(o.reg.UC_X86_REG_ESP)
        cpu.mem_write(stack,struct.pack('<II',o.stop,o.inputs))
        o._run(0x46d1d0,o.stop,timeout=10000000,count=100000000)
        actual=bytes(cpu.mem_read(o.inputs,0x820))
        if actual!=expected:
            offset=next(i for i,(a,b) in enumerate(zip(actual,expected)) if a!=b)
            raise AssertionError((vehicle,hex(offset),actual[offset:offset+4].hex(),expected[offset:offset+4].hex()))
        reports.append(dict(vehicle_id=vehicle,idle_rpm=struct.unpack_from('<i',actual,0x6c)[0],
            maximum_rpm=struct.unpack_from('<i',actual,0x70)[0],
            maximum_torque_sample=max(struct.unpack_from('<25f',actual,0x80))))
    return dict(cases=len(reports),vehicles=reports,maximum_absolute_error=0,
        scope='full original unboosted normal-carb builder/solver/curve finalizer against authored reconstruction from selected actual catalogue loaders; full configuration bytes exact',
        complete_vehicle_assembly=False,original_runtime_driving_tested=False)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('executable',type=Path)
    p.add_argument('database',type=Path);p.add_argument('--vehicles',type=int,nargs='+',default=[101])
    a=p.parse_args();print(json.dumps(verify(a.executable,a.database,a.vehicles)))
