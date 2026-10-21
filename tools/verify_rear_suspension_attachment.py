"""Characterize the special rear-suspension branch of original 0x52df00."""
import argparse
from pathlib import Path
import struct

from client.fce import Model, Part
from client.scene import attach_rear_suspension
from tools.native_oracle import DynoOracle


def _model(names, origins):
    image = bytearray(0x2000)
    struct.pack_into('<I', image, 0x11c, len(names))
    for index, (name, origin) in enumerate(zip(names, origins)):
        encoded = name.encode('ascii')+b'\0'
        image[0xe28+index*0x40:0xe28+index*0x40+len(encoded)] = encoded
        struct.pack_into('<3f', image, 0x120+index*12, *origin)
    return image


def _call(oracle, body_name, body_origin, component_names, component_origins, lod):
    cpu=oracle.cpu
    base=0x74000000
    if not getattr(oracle,'_attachment_memory_mapped',False):
        cpu.mem_map(base,0x100000)
        oracle._attachment_memory_mapped=True
    body,node,component,render=(base+offset for offset in
                                (0x10000,0x2000,0x30000,0x50000))
    cpu.mem_write(body,bytes(_model((body_name,),(body_origin,))))
    cpu.mem_write(component,bytes(_model(component_names,component_origins)))
    cpu.mem_write(node,bytes(0x400))
    cpu.mem_write(node+4,struct.pack('<I',component))
    cpu.mem_write(node+0x18,struct.pack('<I',0)) # Empty component-class prefix.
    cpu.mem_write(node+0x338,struct.pack('<I',0x80e9))
    cpu.mem_write(render,bytes(0x4000))
    oracle.call(0x52df00,(body,node,render,lod,0),instruction_limit=1_000_000)
    count,=struct.unpack('<I',cpu.mem_read(render,4))
    record=bytes(cpu.mem_read(render+4,36))
    changed=bytes(cpu.mem_read(component,0x2000))
    return count,record,changed


def verify(executable):
    oracle=DynoOracle(executable)
    marker=(2.5,-3.0,4.25)
    reports=[]
    for lod,prefix in enumerate((':PH',':PM',':PS',':PT')):
        count,record,component=_call(oracle,':PPrearsusp',marker,
            (prefix+'rearsusp',),((9.0,8.0,7.0),),lod)
        model_pointer,=struct.unpack_from('<I',record,4)
        part_index,=struct.unpack_from('<H',record,12)
        flags,=struct.unpack_from('<I',record,16)
        record_type,=struct.unpack_from('<I',record,20)
        origin=struct.unpack_from('<3f',component,0x120)
        attached, portable=attach_rear_suspension(
            Part(':PPrearsusp',marker,(),(),()),
            Model((Part(prefix+'rearsusp',(9.0,8.0,7.0),(),(),()),),0),
            lod, model_pointer)
        expected=(1,portable.words[1],portable.words[3],portable.words[4],
                  portable.words[5],attached.origin)
        actual=(count,model_pointer,part_index,flags,record_type,origin)
        if actual!=expected:
            raise AssertionError((lod,actual,expected))
        reports.append(lod)
    count,_,component=_call(oracle,':PPrearsusp',marker,
        (':PHother',),((9.0,8.0,7.0),),0)
    if count!=0 or struct.unpack_from('<3f',component,0x120)!=(9.0,8.0,7.0):
        raise AssertionError(('missing-component',count))
    return {'cases':len(reports)+1,'max_error':0,'original_entry':'0x52df00',
            'scope':'rear-suspension marker branch, :PH/:PM/:PS/:PT selection, origin rebasing and missing part'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable',type=Path)
    print(verify(parser.parse_args().executable))


if __name__=='__main__':
    main()
