"""Complete original startup coefficient calls on authored tire configurations."""
import argparse
import itertools
import json
import struct
from client.startup_balance import startup_load_coefficient,startup_balance_coefficient,startup_brake_balance,brake_diameter,brake_capacity
from tools.native_oracle import DynoOracle


def cases():
    for mass,fraction,widths,curves in itertools.product((575.,1000.,1800.),(.35,.5,.65),
            ((205.,210.,285.,210.),(110.,210.,400.,210.)),(0,1,2)):
        config=bytearray(0x820)
        for offset,value in ((0x20,mass),(0x28,200.),(0x2c,2.692),(0x30,1.4),(0x34,1.6),(0x38,.5334),
                (0x3c,fraction),(0xfc,15000.),(0x104,18000.),(0x124,widths[0]),(0x144,widths[1]),
                (0x228,widths[2]),(0x248,widths[3]),(0x148,.03),(0x24c,.04),
                (0x128,70.),(0x12c,15.),(0x22c,60.),(0x230,16.),(0x140,.8),(0x244,.9)):
            struct.pack_into('<f',config,offset,value)
        for offset,value in ((0x5d0,curves),(0x5d4,curves),(0x5d8,curves*5),
                (0x5f0,2-curves),(0x5f4,2-curves),(0x5f8,20-curves*3)):
            struct.pack_into('<I',config,offset,value)
        for offset,factor in ((0x150,200.),(0x1b8,curves*60.),(0x254,250.),(0x2bc,curves*70.)):
            struct.pack_into('<26f',config,offset,*(factor*(i*.1+1.) for i in range(26)))
        yield bytes(config)


def verify(executable,database=None):
    o=DynoOracle(executable);cpu=o.cpu;count=0
    records=list(cases());stock=0
    if database:
        from client.catalogue import Catalogue
        from client.dyno import load_flow_templates
        from client.mechanical_assembly import assemble_stock_vehicle
        from client.tire_templates import load_tire_templates
        catalogue=Catalogue.load(database);flows=load_flow_templates(executable);tires=load_tire_templates(database)
        for vehicle in range(101,109):
            assembled=assemble_stock_vehicle(catalogue,vehicle,flows,tire_templates=tires,percent_damage=0,item_wear=0)
            if assembled.status!=1:raise ValueError((vehicle,'stock assembly failed'))
            records.append(assembled.configuration);stock+=1
    cpu.mem_write(o.stub,b'\xd9\x1d'+struct.pack('<I',o.inputs+0x9000)+b'\xe9'+struct.pack('<i',o.stop-(o.stub+11)))
    double_stub=o.stub+0x100
    cpu.mem_write(double_stub,b'\xdd\x1d'+struct.pack('<I',o.inputs+0x9000)+b'\xe9'+struct.pack('<i',o.stop-(double_stub+11)))
    diameter_count=capacity_count=0
    for code in (*range(23),0xffffffff):
        o._reset();stack=cpu.reg_read(o.reg.UC_X86_REG_ESP);cpu.mem_write(stack,struct.pack('<II',o.stub,code))
        o._run(0x538820,o.stop)
        if bytes(cpu.mem_read(o.inputs+0x9000,4))!=struct.pack('<f',brake_diameter(code)):raise AssertionError(('brake diameter',code))
        diameter_count+=1
    for diameter,material,construction,pressure,auxiliary in itertools.product((.2032,.3175,.4572),range(4),range(3),(.25,1.),(False,True)):
        o._reset();stack=cpu.reg_read(o.reg.UC_X86_REG_ESP)
        cpu.mem_write(stack,struct.pack('<IfIIfI',double_stub,diameter,material,construction,pressure,int(auxiliary)))
        o._run(0x5399d0,o.stop)
        expected=struct.pack('<d',brake_capacity(diameter,material,construction,pressure,auxiliary))
        actual=bytes(cpu.mem_read(o.inputs+0x9000,8))
        if actual!=expected:raise AssertionError(('brake capacity',diameter,material,construction,pressure,auxiliary,struct.unpack('<d',actual)[0],struct.unpack('<d',expected)[0]))
        capacity_count+=1
    for config in records:
        for alternate in (False,True):
            cpu.mem_write(0xa384c8,struct.pack('<I',int(alternate)))
            for entry,wanted in ((0x54a0e0,startup_load_coefficient(config)),
                    (0x53acc0,startup_balance_coefficient(config,alternate_load=alternate)),
                    (0x53b040,startup_brake_balance(config))):
                o._reset();cpu.mem_write(o.inputs,config)
                stack=cpu.reg_read(o.reg.UC_X86_REG_ESP);cpu.mem_write(stack,struct.pack('<II',o.stub,o.inputs))
                o._run(entry,o.stop,count=50000)
                actual=bytes(cpu.mem_read(o.inputs+0x9000,4));expected=struct.pack('<f',wanted)
                if actual!=expected:raise AssertionError((count,hex(entry),alternate,actual.hex(),expected.hex(),
                    struct.unpack('<f',actual)[0],wanted))
                count+=1
    return dict(calls=count,configurations=len(records),stock_configurations=stock,brake_diameter_calls=diameter_count,
        brake_capacity_calls=capacity_count,maximum_absolute_error=0,
        scope='complete original 0x54a0e0, 0x53acc0, 0x53b040, 0x538820 and 0x5399d0 with real response children; no integrated handling claim',
        integrated_handling_verified=False)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('executable');parser.add_argument('--database')
    args=parser.parse_args();print(json.dumps(verify(args.executable,args.database)))
