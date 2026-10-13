"""Verify original model-brand lookup/copies after family text enrichment."""
import argparse
import json
import struct
from client.owned_parts import apply_owned_model_brand, apply_owned_vehicle_price
from tools.native_oracle import DynoOracle


def verify(executable):
    oracle = DynoOracle(executable)
    cpu, reg = oracle.cpu, oracle.reg
    cases = ((7,dict(Brand='Maker',PicName='picture')),
             (7,dict(Brand='b'*90,PicName='p'*20)),
             (7,dict(Brand=None,PicName=None)),(99,None))
    for identifier,row in cases:
        oracle._reset()
        initial = b'Z'*1596
        cpu.mem_write(oracle.inputs,initial)
        cache = bytearray(1596*2)
        struct.pack_into('<I',cache,0x5f8,6)
        struct.pack_into('<I',cache,1596+0x5f8,7)
        if row is not None:
            for offset,count,key in ((0x1c0,8,'PicName'),(0x347,63,'Brand')):
                value = '' if row[key] is None else row[key]
                cache[1596+offset:1596+offset+count] = value.encode('cp1252')[:count].ljust(count,b'\0')
        cpu.mem_write(oracle.inputs+0x3000,bytes(cache))
        cpu.mem_write(0xb17520,struct.pack('<II',oracle.inputs+0x3000,2))
        cpu.mem_write(oracle.frame-0x2c,struct.pack('<I',identifier))
        cpu.reg_write(reg.UC_X86_REG_EBX,oracle.inputs+0x1e3)
        oracle._run(0x669591,0x6695fb,count=100000)
        if bytes(cpu.mem_read(oracle.inputs,1596)) != apply_owned_model_brand(initial,row,text_encoding='cp1252'):
            raise ValueError('original model-brand copy differs')
    for identifier,price in ((101,0),(101,123),(20001,123)):
        oracle._reset()
        initial = bytearray(b'Z'*1596)
        struct.pack_into('<i',initial,0,identifier)
        cpu.mem_write(oracle.inputs,bytes(initial))
        cpu.mem_write(oracle.frame-0x24,struct.pack('<i',price))
        cpu.reg_write(reg.UC_X86_REG_ESI,oracle.inputs)
        oracle._run(0x669714,0x669722,count=100)
        if bytes(cpu.mem_read(oracle.inputs,1596)) != apply_owned_vehicle_price(bytes(initial),price):
            raise ValueError('original final vehicle price override differs')
    return {'matched_model_brand_cases':len(cases),'matched_final_vehicle_price_cases':3,
            'scope':'original cache lookup and copying, supplied cached records; cache query excluded'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    print(json.dumps(verify(parser.parse_args().executable),indent=2))
