"""Compare linked owner-node class/LOD lookup with original 0x52e670."""
import argparse
from pathlib import Path
import struct

from client.fce import Model, Part
from client.scene import ComponentModelNode, select_component_node
from tools.native_oracle import DynoOracle

CLASS_PREFIXES=('', 'LF', 'RF', 'LR', 'RR', 'L', 'R', 'A', 'B', 'C', 'F', 'R')


def _model_image(names):
    image=bytearray(0x3000)
    struct.pack_into('<I',image,0x11c,len(names))
    for index,name in enumerate(names):
        encoded=name.encode('ascii')+b'\0'
        image[0xe28+index*0x40:0xe28+index*0x40+len(encoded)]=encoded
    return bytes(image)


def verify(executable):
    oracle=DynoOracle(executable)
    cpu=oracle.cpu
    base=0x74000000
    cpu.mem_map(base,0x100000)
    nodes_base,models_base,listing=(base+offset for offset in
                                    (0x1000,0x10000,0x60000))
    suffix_ptr,class_ptr,out_model,out_index=(base+offset for offset in
                                              (0x70000,0x70100,0x70200,0x70204))
    cases=[]
    for class_index,prefix in enumerate(CLASS_PREFIXES):
        cases.append(([ (class_index,(':PHother',':PTtire')) ],prefix,3,0))
    cases.extend((
        ([(6,(':PHtire',)),(11,(':PTtire',))],'R',3,1),
        ([(11,(':PHtire',)),(6,(':PHtire',))],'R',0,0),
        ([(1,(':PHtire',))],'RF',3,None),
        ([(5,(':PHother',))],'L',0,None),
    ))
    for case_index,(definitions,prefix,lod,expected_node) in enumerate(cases):
        model_nodes=[]
        for index,(class_index,names) in enumerate(definitions):
            node=nodes_base+index*0x400
            model=models_base+index*0x3000
            next_node=(nodes_base+(index+1)*0x400 if index+1<len(definitions) else 0)
            cpu.mem_write(node,bytes(0x33c))
            cpu.mem_write(node,struct.pack('<II',next_node,model))
            cpu.mem_write(node+0x18,struct.pack('<I',class_index))
            cpu.mem_write(model,_model_image(names))
            decoded=Model(tuple(Part(name,(0,0,0),(),(),()) for name in names),0)
            model_nodes.append(ComponentModelNode(class_index,decoded,model))
        head=nodes_base if definitions else 0
        cpu.mem_write(listing,bytes(0x2000))
        cpu.mem_write(suffix_ptr,b'tire\0')
        cpu.mem_write(class_ptr,prefix.encode('ascii')+b'\0')
        cpu.mem_write(out_model,struct.pack('<I',0xffffffff))
        cpu.mem_write(out_index,struct.pack('<I',0xffffffff))
        oracle.call(0x52e670,(head,listing,suffix_ptr,class_ptr,out_model,lod,out_index),
                    instruction_limit=200_000)
        count,=struct.unpack('<I',cpu.mem_read(listing,4))
        native_model,=struct.unpack('<I',cpu.mem_read(out_model,4))
        native_node,=struct.unpack('<I',cpu.mem_read(out_index,4))
        expected=select_component_node(model_nodes,prefix,'tire',lod)
        actual_index=expected.node_index if expected else None
        if actual_index!=expected_node or count!=(1 if expected else 0):
            raise AssertionError((case_index,actual_index,expected_node,count))
        if expected:
            record=bytes(cpu.mem_read(listing+4,36))
            expected_handle=model_nodes[expected.node_index].model_handle
            part_index,=struct.unpack_from('<H',record,12)
            flags,=struct.unpack_from('<I',record,16)
            fields=(native_model,native_node,part_index,flags)
            # param_7 is the appended render-record index, not the owner-node index.
            wanted=(expected_handle,0,expected.part_index,
                    expected.record.words[4])
            if fields!=wanted:
                raise AssertionError((case_index,fields,wanted))
    return {'cases':len(cases),'max_error':0,'original_entry':'0x52e670',
            'scope':'all 12 native class slots including duplicate R, LOD-major/node-major priority, records and misses'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable',type=Path)
    print(verify(parser.parse_args().executable))


if __name__=='__main__':
    main()
