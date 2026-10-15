"""Full configuration comparison for the original postload numeric tail."""
import argparse
import json
import struct
from client.assembly_finalization import WEIGHTED_SLOTS,finalize_loaded_configuration
from tools.assembly_weight_oracle import cases as weight_cases,configuration
from tools.native_oracle import DynoOracle


def cases():
    for index,args in enumerate(weight_cases()):
        image=bytearray(configuration(args))
        # The weighted-divisor calculation also has slots absent from the axle
        # mass helper. Distinct values prevent accidentally swapping their roles.
        for offset,value in ((0x478,13.125),(0x4ac,29.3),(0x20,975.25),
                (0x28,170.125),(0x610,0. if index%4<2 else .17),
                (0x620,0. if index%2==0 else .31)):
            struct.pack_into('<f',image,offset,value)
        for ordinal,(offset,_) in enumerate((*WEIGHTED_SLOTS,(0x580,0x574))):
            struct.pack_into('<i',image,offset,(index+ordinal)%10)
        struct.pack_into('<i',image,0x57c,index%4)
        yield bytes(image)


def verify(executable):
    o=DynoOracle(executable);count=0
    for image in cases():
        o._reset();o.cpu.mem_write(o.inputs,image)
        o.cpu.reg_write(o.reg.UC_X86_REG_EBX,o.inputs)
        o._run(0x54e8ea,0x54ea89,count=2000)
        actual=bytes(o.cpu.mem_read(o.inputs,0x820))
        expected=finalize_loaded_configuration(image,components_loaded=True)
        if actual!=expected:
            offset=next(i for i,(a,b) in enumerate(zip(actual,expected)) if a!=b)
            raise AssertionError((count,hex(offset),actual[offset:offset+4].hex(),expected[offset:offset+4].hex()))
        count+=1
    return dict(cases=count,maximum_absolute_error=0,
        scope='0x54e8ea..0x54ea89 including actual 0x53b590; all 0x820 configuration bytes exact; component loaders/quality updates and final engine curves excluded')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('executable')
    print(json.dumps(verify(p.parse_args().executable)))
