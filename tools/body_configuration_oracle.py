"""Bounded shipped body numeric initializer; optional actual catalogue case."""
import argparse
import json
import struct

from client.body_configuration import initialize_body_configuration,stock_body_configuration
from client.physics_data import PhysicsRecord
from tools.native_oracle import DynoOracle


def cases():
    # Authored records deliberately distinguish nearest-even from truncation,
    # low-byte stores from int stores, repeated copies, and untouched bytes.
    for number in (-2147483904.,-257.9,-2.5,-1.5,-.5,0.,.5,1.5,2.5,255.9,256.9,2147483648.):
        for ordinal in (7,8,12,13,14,15,19,21,22,33,38,39):
            values=[(i+1)*.125 for i in range(39)]
            values[ordinal-1]=number
            yield PhysicsRecord(20001,1,575.25,tuple(values))
    yield PhysicsRecord(20001,1,0.,tuple(-0. for _ in range(39)))


def verify(executable, database=None):
    o=DynoOracle(executable);cpu=o.cpu;reg=o.reg
    records=list(cases())
    if database is not None:
        from client.catalogue import Catalogue
        catalogue=Catalogue.load(database)
        body=stock_body_configuration(catalogue)
        records.append(catalogue.physics[(body.part_type_id,body.physics_ordinal)])
    for index,record in enumerate(records):
        o._reset()
        component=o.inputs;config=o.inputs+0x1000
        image=bytearray(0x100)
        struct.pack_into('<I',image,0x14,39)
        struct.pack_into('<f',image,0x30,record.mass)
        struct.pack_into('<39f',image,0x3c,*record.values)
        initial=bytes([0xa5])*0x820
        cpu.mem_write(component,bytes(image));cpu.mem_write(config,initial)
        cpu.mem_write(o.frame+8,struct.pack('<I',config))
        cpu.reg_write(reg.UC_X86_REG_EDI,component)
        o._run(0x54a3c1,0x54a594,count=5000)
        actual=bytes(cpu.mem_read(config,0x820))
        expected=initialize_body_configuration(record,initial_image=initial).image
        if actual!=expected:
            offset=next(i for i,(a,b) in enumerate(zip(actual,expected)) if a!=b)
            raise AssertionError((index,hex(offset),actual[offset:offset+4].hex(),expected[offset:offset+4].hex()))
    return {'cases':len(records),'maximum_absolute_error':0,
        'actual_vehicle_101_included':database is not None,
        'scope':'0x54a3c1 through 0x54a594; actual CRT conversion helper; full 0x820 configuration comparison; semantic validator and quality wrapper excluded'}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('executable');p.add_argument('--database')
    args=p.parse_args();print(json.dumps(verify(args.executable,args.database)))
