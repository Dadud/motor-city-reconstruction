"""Compare the simple generic marker branch of original 0x52df00."""
import argparse
from pathlib import Path
import struct

from client.fce import Model, Part
from client.scene import attach_component_marker
from tools.native_oracle import DynoOracle


def _image(names, origins, vertices=()):
    image=bytearray(0x3000)
    struct.pack_into('<I',image,0x11c,len(names))
    struct.pack_into('<I',image,0x58,len(vertices))
    for index,(name,origin) in enumerate(zip(names,origins)):
        data=name.encode('ascii')+b'\0'
        image[0xe28+index*0x40:0xe28+index*0x40+len(data)]=data
        struct.pack_into('<3f',image,0x120+index*12,*origin)
    for index,vertex in enumerate(vertices):
        struct.pack_into('<3f',image,0x5c+index*12,*vertex)
    return image


def _call(oracle, marker_name, class_index, lod, flags=0):
    cpu=oracle.cpu
    base=0x74000000
    if not getattr(oracle,'_generic_attachment_memory_mapped',False):
        cpu.mem_map(base,0x100000)
        oracle._generic_attachment_memory_mapped=True
    body,node,component,render=(base+offset for offset in
                                (0x10000,0x2000,0x30000,0x50000))
    marker_origin=(20.0,30.0,40.0)
    original_origins=((2.0,3.0,4.0),(5.0,6.0,7.0))
    nested_origin=(4.0,5.0,6.0)
    original_vertices=((8.0,10.0,12.0),(0.0,1.0,2.0))
    suffix='engine' if marker_name==':PPengine' else 'fog'
    nested_name=':PPmanifold' if suffix=='engine' else ':PPLchild'
    cpu.mem_write(body,bytes(_image((marker_name,),(marker_origin,))))
    cpu.mem_write(component,bytes(_image((':PH'+suffix,':PT'+suffix,nested_name),
        original_origins+(nested_origin,),original_vertices)))
    cpu.mem_write(node,bytes(0x400))
    cpu.mem_write(node+4,struct.pack('<I',component))
    cpu.mem_write(node+0x18,struct.pack('<I',class_index))
    cpu.mem_write(render,bytes(0x4000))
    oracle.call(0x52df00,(body,node,render,lod,flags),instruction_limit=1_000_000)
    count,=struct.unpack('<I',cpu.mem_read(render,4))
    record=bytes(cpu.mem_read(render+4,36))
    changed=bytes(cpu.mem_read(component,0x3000))
    return (count,record,changed,component,marker_origin,original_origins,
            original_vertices,suffix,nested_name)


def verify(executable):
    oracle=DynoOracle(executable)
    cases=((':PPLfog',5,0,0,0),(':PPRfog',6,0,0,0),
           (':PPRfog',6,3,1,0),(':PPengine',0,0,0,0x10000))
    for marker,class_index,lod,selected_index,param_flags in cases:
        count,record,image,model,marker_origin,origins,vertices,suffix,nested_name=_call(
            oracle,marker,class_index,lod,param_flags)
        if count!=1:
            raise AssertionError((marker,lod,'count',count))
        model_pointer,=struct.unpack_from('<I',record,4)
        part_index,=struct.unpack_from('<H',record,12)
        flags,=struct.unpack_from('<I',record,16)
        mesh_type,=struct.unpack_from('<I',record,20)
        portable_model=Model(tuple(Part(name,origin,vertices if index<2 else (),(),())
            for index,(name,origin) in enumerate(zip(
                (':PH'+suffix,':PT'+suffix,nested_name),
                origins+((4.0,5.0,6.0),)))),0)
        portable=attach_component_marker(Part(marker,marker_origin,(),(),()),
            portable_model,lod,model)
        if portable is None:
            raise AssertionError((marker,lod,'portable selector missed'))
        transformed,portable_index,portable_record=portable
        wanted_flags=(1<<lod)|(0x40 if marker.startswith(':PPR') else 0)
        if (model_pointer,part_index,flags,mesh_type)!=(model,selected_index,wanted_flags,0):
            raise AssertionError((marker,lod,model_pointer,part_index,flags,mesh_type))
        if (portable_index,portable_record.words[1],portable_record.words[3],
            portable_record.words[4],portable_record.words[5]) != (
                part_index,model_pointer,part_index,flags,mesh_type):
            raise AssertionError((marker,lod,'portable render record'))
        new_origin=struct.unpack_from('<3f',image,0x120+selected_index*12)
        if new_origin!=transformed.parts[selected_index].origin:
            raise AssertionError((marker,lod,'origin',new_origin,
                                  transformed.parts[selected_index].origin))
        observed_nested=struct.unpack_from('<3f',image,0x120+2*12)
        if observed_nested!=transformed.parts[2].origin:
            raise AssertionError((marker,lod,'nested marker',observed_nested,
                                  transformed.parts[2].origin))
        if lod==0:
            expected_vertices=[]
            anchor=origins[selected_index]
            mirror=marker.startswith(':PPR')
            for vertex in vertices:
                x=-(vertex[0]-anchor[0]) if mirror else vertex[0]-anchor[0]
                expected_vertices.append((x+marker_origin[0],
                    vertex[1]-anchor[1]+marker_origin[1],
                    vertex[2]-anchor[2]+marker_origin[2]))
            observed=tuple(struct.unpack_from('<3f',image,0x5c+i*12)
                           for i in range(len(vertices)))
            if (observed!=tuple(expected_vertices) or
                    observed!=transformed.parts[selected_index].vertices):
                raise AssertionError((marker,lod,'vertices',observed,expected_vertices,
                                      transformed.parts[selected_index].vertices))
        else:
            observed=tuple(struct.unpack_from('<3f',image,0x5c+i*12)
                           for i in range(len(vertices)))
            if (observed!=vertices or
                    observed!=transformed.parts[selected_index].vertices):
                raise AssertionError((marker,lod,'unexpected vertex mutation',observed))
    return {'cases':len(cases),'max_error':0,'original_entry':'0x52df00',
            'scope':'generic L/R/engine marker lookup, engine gate, option fallback, mirror flag, selected-part and nested-marker transforms'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable',type=Path)
    print(verify(parser.parse_args().executable))


if __name__=='__main__':
    main()
