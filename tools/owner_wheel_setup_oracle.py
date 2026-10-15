"""Full original wheel setup with explicit prior owner/configuration inputs."""
import argparse
import itertools
import json
import struct
from client.owner_wheel_setup import initialize_owner_wheels,adjust_owner_stance
from tools.native_oracle import DynoOracle


def cases():
    for radii,has_parts,mode in itertools.product(((.3,.3),(.37,.42),(.5,.31),(.3333333,.4123456)),(0,1),range(5)):
        # Nonzero finite sentinels expose accidental writes and byte-sized stores.
        owner=bytearray(struct.pack('<f',1.25)*0x800);config=bytearray(0x820)
        for offset,value in ((0xd0,.65),(0x18ec,radii[0]),(0x18f0,radii[1]),(0x18c4,1.4),(0x18c8,-1.3)):
            struct.pack_into('<f',owner,offset,value)
        struct.pack_into('<I',owner,0x490,has_parts)
        for offset,value in ((0x20,1234.567),(0x30,1.4),(0x34,1.6),(0x58,.65),
            (0x11c,.18),(0x120,.2),(0x124,205),(0x228,285),(0x144,210),
            (0x138,.7),(0x23c,.8),(0x700,8.),(0x70c,12.),(0x220,10.),(0x324,13.),
            (0x134,5.5),(0x238,6.5),(0x140,.9),(0x244,1.1)):
            struct.pack_into('<f',config,offset,value)
        struct.pack_into('<i',config,0x224,mode);struct.pack_into('<i',config,0x328,3-mode)
        config[0x60:0x64]=((0,0,0,0),(1,1,0,0),(0,0,1,1),(1,0,1,0),(1,1,1,1))[mode]
        config[0xe4]=mode%2
        if mode==4:struct.pack_into('<f',config,0x700,0.)
        yield bytes(owner),bytes(config)


def verify(executable,database=None):
    records=list(cases());stock=0
    if database:
        from client.catalogue import Catalogue
        from client.dyno import load_flow_templates
        from client.mechanical_assembly import assemble_stock_vehicle
        from client.tire_templates import load_tire_templates
        catalogue=Catalogue.load(database);templates=load_flow_templates(executable);tires=load_tire_templates(database)
        for vehicle in range(101,109):
            result=assemble_stock_vehicle(catalogue,vehicle,templates,tire_templates=tires,percent_damage=0,item_wear=0)
            if result.status!=1:raise ValueError((vehicle,'stock assembly failed'))
            # Prior geometry remains an explicit authored observation, not a
            # claim to have recovered these models' complete startup.
            for owner,_ in list(cases())[:2]:records.append((owner,result.configuration));stock+=1
    o=DynoOracle(executable);cpu=o.cpu;count=0
    for index,(owner,config) in enumerate(records):
        image=bytearray(owner);struct.pack_into('<I',image,0x1c94,o.inputs+0x3000);image=bytes(image)
        expected=initialize_owner_wheels(image,config,assembly_finalized=True)
        o._reset();cpu.mem_write(o.inputs,image);cpu.mem_write(o.inputs+0x3000,config)
        stack=cpu.reg_read(o.reg.UC_X86_REG_ESP);cpu.mem_write(stack,struct.pack('<II',o.stop,o.inputs))
        o._run(0x53b8a0,o.stop,count=50000)
        actual=bytes(cpu.mem_read(o.inputs,0x2000))
        if actual!=expected:
            offset=next(i for i,(a,b) in enumerate(zip(actual,expected)) if a!=b)
            raise AssertionError((index,hex(offset),actual[offset:offset+4].hex(),expected[offset:offset+4].hex()))
        cpu.mem_write(o.inputs,image);o._reset();stack=cpu.reg_read(o.reg.UC_X86_REG_ESP)
        cpu.mem_write(stack,struct.pack('<II',o.stop,o.inputs));o._run(0x53b3c0,o.stop,count=5000)
        if bytes(cpu.mem_read(o.inputs,0x2000))!=adjust_owner_stance(image):raise AssertionError((index,'stance'))
        count+=1
    return dict(wheel_setup_cases=count,standalone_stance_cases=count,stock_configuration_cases=stock,
        maximum_absolute_error=0,scope='complete original 0x53b8a0 and 0x53b3c0; all owner bytes exact; supplied prior geometry',
        full_model_startup_verified=False)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('executable');p.add_argument('--database')
    a=p.parse_args();print(json.dumps(verify(a.executable,a.database)))
