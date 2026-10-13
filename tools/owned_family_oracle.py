"""Verify original family lookup and text override instruction range."""
import argparse
import json
import struct
from client.owned_parts import OwnedEngineFamily
from tools.native_oracle import DynoOracle


def verify(executable):
    from unicorn import UC_HOOK_CODE
    oracle = DynoOracle(executable)
    cpu, reg = oracle.cpu, oracle.reg
    def loaded(cpu,address,size,unused):
        stack = cpu.reg_read(reg.UC_X86_REG_ESP)
        ret = struct.unpack('<I',bytes(cpu.mem_read(stack,4)))[0]
        cpu.reg_write(reg.UC_X86_REG_EAX,1)
        cpu.reg_write(reg.UC_X86_REG_ESP,stack+4)
        cpu.reg_write(reg.UC_X86_REG_EIP,ret)
    hook = cpu.hook_add(UC_HOOK_CODE,loaded,begin=0x668af0,end=0x668af0)
    matched = 0
    try:
        for selected,cache_present in ((10,True),(10,False),(11,True),(-1,True)):
            oracle._reset()
            initial = bytearray(b'Z'*1596)
            struct.pack_into('<i',initial,0x203,selected)
            cpu.mem_write(oracle.inputs,bytes(initial))
            table = oracle.inputs+0x2000
            record = bytearray(0x6c*2)
            struct.pack_into('<ii',record,0,10,7)
            record[8:8+64] = (b'Family Brand\0').ljust(64,b'\0')
            record[0x48:0x48+26] = (b'Family Name\0').ljust(26,b'\0')
            record[0x62:0x62+8] = (b'Short\0').ljust(8,b'\0')
            struct.pack_into('<i',record,0x6c,-1)
            cpu.mem_write(table,bytes(record))
            cpu.mem_write(0xb298e8,struct.pack('<I',table))
            brand_slot = bytearray(1596)
            struct.pack_into('<I',brand_slot,0x5f8,7)
            brand_slot[0x347:0x347+64] = b'Cached Brand\0'.ljust(64,b'\0')
            cpu.mem_write(oracle.inputs+0x3000,bytes(brand_slot))
            cpu.mem_write(0xb17520,struct.pack('<II',oracle.inputs+0x3000,int(cache_present)))
            cpu.reg_write(reg.UC_X86_REG_EBX,oracle.inputs+0x1e3)
            oracle._run(0x669498,0x669541,count=100000)
            expected = bytes(initial)
            if selected == 10:
                family = OwnedEngineFamily(10,7,'Family Brand','Family Name','Short')
                expected = family.apply(expected,text_encoding='cp1252',
                    brand_cache_name='Cached Brand' if cache_present else None)
            if bytes(cpu.mem_read(oracle.inputs,1596)) != expected:
                raise ValueError('original family text override differs')
            matched += 1
    finally:
        cpu.hook_del(hook)
    return {'matched_family_override_cases':matched,
            'scope':'original lookup and copies, supplied family/brand caches; loader boundary substituted'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    print(json.dumps(verify(parser.parse_args().executable),indent=2))
