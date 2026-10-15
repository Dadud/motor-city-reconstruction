"""Compare nineteen selected stock loader calls in sequence, not full assembly."""
import argparse
import json
import struct
from client.body_configuration import stock_body_configuration
from client.catalogue import Catalogue
from client.mechanical_loaders import MECHANICAL_LOADERS
from client.mechanical_parts import expand_mechanical_parts
from tools.inspect_stock_mechanical import stock_slots,selected_parts
from tools.mechanical_loaders_oracle import ENTRIES
from tools.native_oracle import DynoOracle


def verify(executable,database,vehicle=101):
    catalogue=Catalogue.load(database)
    parts=expand_mechanical_parts(stock_slots(catalogue,vehicle,percent_damage=0,item_wear=0))
    image=stock_body_configuration(catalogue,vehicle).image
    o=DynoOracle(executable);cpu=o.cpu;target=o.inputs;source=o.inputs+0x1000
    cpu.mem_write(target,image);count=0
    entries=dict(ENTRIES) # Engine loader joins the other six original bodies.
    entries[160001]=0x54a5a0
    for kind,part in selected_parts(parts):
        o._reset();cpu.mem_write(source,part.image)
        stack=cpu.reg_read(o.reg.UC_X86_REG_ESP)
        cpu.mem_write(stack,struct.pack('<III',o.stop,target,source))
        o._run(entries[kind],o.stop,count=20000)
        expected=MECHANICAL_LOADERS[kind](image,part.image)
        status=cpu.reg_read(o.reg.UC_X86_REG_EAX)
        if status!=expected.status or status!=0:
            raise AssertionError(('stock component rejected',kind,part.attachment,status,expected.status))
        if bytes(cpu.mem_read(target,0x820))!=expected.configuration:
            raise AssertionError(('stock configuration mismatch',kind,part.attachment))
        if bytes(cpu.mem_read(source,0x984))!=expected.component:
            raise AssertionError(('stock component mismatch',kind,part.attachment))
        image=expected.configuration;count+=1
    return dict(vehicle_id=vehicle,selected_loader_calls=count,maximum_absolute_error=0,
        source_slots=len(catalogue.vehicle(vehicle).parts),expanded_components=len(parts),
        scope='actual catalogue parts with authored zero-damage/zero-wear fixture state; selected original loaders in dispatcher relative order; full images exact after every call; other loaders skipped',
        complete_assembly=False,live_driving_tested=False)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('executable');p.add_argument('database')
    p.add_argument('--vehicle',type=int,default=101)
    args=p.parse_args();print(json.dumps(verify(args.executable,args.database,args.vehicle)))
