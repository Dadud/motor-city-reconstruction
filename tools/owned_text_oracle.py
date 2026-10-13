"""Verify original query-text copies before family/type-specific overrides."""
import argparse
import json
import struct
from client.owned_parts import OwnedPartMetadata
from tools.native_oracle import DynoOracle


def verify(executable):
    oracle = DynoOracle(executable)
    cpu, reg = oracle.cpu, oracle.reg
    cases = ((None,None,None,None,None),
             ('Body','Coupe','Short','Details','coupe'),
             ('t'*80,'m'*63,'s'*63,'e'*351,'f'*8),
             ('Caf\u00e9','Mod\u00e8le','','',''))
    for type_name,model,short,extra,filename in cases:
        metadata = OwnedPartMetadata(20001,200,500,1000,1955,3,0,7,
                                     type_name,model,short,extra,filename)
        oracle._reset()
        initial = b'Z'*1596
        cpu.mem_write(oracle.inputs,initial)
        for displacement,capacity,value in ((-0x158,64,type_name),(-0x118,64,model),
                (-0x2f8,352,extra),(-0x88,9,filename),(-0xc8,1,None),(-0x198,64,short)):
            data = b'' if value is None else value.encode('cp1252')
            cpu.mem_write(oracle.frame+displacement,(data+b'\0')[:capacity].ljust(capacity,b'\0'))
        cpu.reg_write(reg.UC_X86_REG_EBX,oracle.inputs+0x1e3)
        # The first range instruction repeats a preceding helper result at
        # offset 0x18; preserve the initial value to isolate only text copies.
        cpu.reg_write(reg.UC_X86_REG_EAX,struct.unpack_from('<I',initial,0x18)[0])
        oracle._run(0x6693a6,0x669498,count=100000)
        expected = metadata.apply_text_fields(initial,text_encoding='cp1252')
        if bytes(cpu.mem_read(oracle.inputs,1596)) != expected:
            raise ValueError('original owned-part query text differs')
    return {'matched_query_text_cases':len(cases),
            'scope':'original copy instructions with supplied query buffers; later overrides excluded'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    print(json.dumps(verify(parser.parse_args().executable),indent=2))
