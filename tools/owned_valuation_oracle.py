"""Compare original post-load x87 arithmetic against authored valuation."""
import argparse
import json
import struct
from client.owned_valuation import PartValuationRates, apply_owned_valuation
from tools.native_oracle import DynoOracle


def verify(executable):
    from unicorn import UC_HOOK_CODE
    oracle = DynoOracle(executable)
    cpu, reg = oracle.cpu, oracle.reg
    present = [True]
    record = oracle.inputs+0x3000
    def rate_lookup(cpu,address,size,unused):
        stack = cpu.reg_read(reg.UC_X86_REG_ESP)
        ret = struct.unpack('<I',bytes(cpu.mem_read(stack,4)))[0]
        cpu.reg_write(reg.UC_X86_REG_EAX,record if present[0] else 0)
        cpu.reg_write(reg.UC_X86_REG_ESP,stack+4+8)
        cpu.reg_write(reg.UC_X86_REG_EIP,ret)
    hook = cpu.hook_add(UC_HOOK_CODE,rate_lookup,begin=0x4bc220,end=0x4bc220)
    cases = ((160001,500,1000,0,0,0),(160001,500,1000,20,250,0),
             (20001,500,900,17,25,0),
             (160001,1,1000,1,1000,0),(160001,500,0,20,500,0),
             (160001,500,1000,100,2000,0),(20001,500,1000,20,250,123.25),
             (20999,500,1000,0,0,5.5),(21000,500,1000,0,0,5.5),
             (160001,2147483647,1,2147483647,-2147483648,0))
    matched = 0
    try:
        for available,repair,scrap in ((True,0.1,0.75),(True,0.2,0.65),(False,0.1,0.75)):
            present[0] = available
            rates = PartValuationRates(repair,scrap)
            for identifier,price,maximum,damage,wear,body_value in cases:
                oracle._reset()
                initial = bytearray(1596)
                struct.pack_into('<I',initial,0,identifier)
                struct.pack_into('<I',initial,0x1e3,123)
                struct.pack_into('<ii',initial,0x1eb,price,maximum)
                struct.pack_into('<f',initial,0x454,body_value)
                struct.pack_into('<I',initial,0x5f8,42)
                struct.pack_into('<ii',initial,0x610,damage,wear)
                struct.pack_into('<ii',initial,0x62c,999,888)
                cpu.mem_write(oracle.inputs,bytes(initial))
                cpu.mem_write(record+0x1e,struct.pack('<dd',repair,scrap))
                cpu.reg_write(reg.UC_X86_REG_ESI,oracle.inputs+0x1e3)
                cpu.mem_write(oracle.frame-0x14,struct.pack('<I',1))
                oracle._run(0x66f944,0x66fb05,count=100000)
                expected = apply_owned_valuation(bytes(initial),rates)
                actual = bytes(cpu.mem_read(oracle.inputs,1596))
                if actual != expected:
                    raise ValueError(f'original valuation differs for {identifier,price,maximum,damage,wear,body_value}: {struct.unpack_from("<ii",actual,0x62c)} != {struct.unpack_from("<ii",expected,0x62c)}')
                matched += 1
    finally:
        cpu.hook_del(hook)
    return {'matched_valuation_cases':matched,
            'scope':'original arithmetic/getters/ftol at 53-bit precision; server-data lookup boundary substituted'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    print(json.dumps(verify(parser.parse_args().executable),indent=2))
