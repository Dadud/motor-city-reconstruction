"""Execute original formatting and category-copy routines on synthetic slots."""
import argparse
import json
import struct
from client.part_type_templates import apply_owned_display_names
from tools.native_oracle import DynoOracle


def verify(executable):
    oracle = DynoOracle(executable)
    cpu, reg = oracle.cpu, oracle.reg
    oracle._reset()
    cpu.mem_write(0xb18014,struct.pack('<I',99))
    oracle._run(0x6538c0,0x6538e0,count=100)
    if struct.unpack('<I',bytes(cpu.mem_read(0xb18014,4)))[0] != 2:
        raise ValueError('original display-mode initializer differs')
    matched = 0
    for mode,identifier,year in ((2,20001,1955),(1,20001,1955),(1,1001,1955),
                                (2,101,1955),(1,101,1899),(2,101,2005)):
        oracle._reset()
        initial = bytearray(b'Z'*1596)
        struct.pack_into('<i',initial,0,identifier)
        struct.pack_into('<i',initial,0x1fb,year)
        initial[0x2c7:0x307] = b'Maker\0'.ljust(64,b'\0')
        initial[0x307:0x347] = b'Model\0'.ljust(64,b'\0')
        template = bytearray(1596)
        struct.pack_into('<i',template,0,identifier)
        template[0x180:0x1c0] = b'Category\0'.ljust(64,b'\0')
        table = oracle.inputs+0x3000
        cpu.mem_write(table,bytes(1596)+bytes(template))
        cpu.mem_write(0xb18014,struct.pack('<III',mode,2,table))
        cpu.mem_write(oracle.inputs,bytes(initial))
        cpu.mem_write(oracle.frame+0xc,struct.pack('<i',identifier))
        cpu.reg_write(reg.UC_X86_REG_EBX,oracle.inputs+0x1e3)
        cpu.reg_write(reg.UC_X86_REG_EDX,oracle.inputs)
        oracle._run(0x66965a,0x6696a1,count=1000000)
        if bytes(cpu.mem_read(oracle.inputs,1596)) != apply_owned_display_names(bytes(initial),bytes(template),mode=mode):
            raise ValueError('original display formatting differs')
        matched += 1
    return {'matched_display_cases':matched,'matched_default_mode_initializers':1,
            'scope':'original formatting including CRT sprintf and category lookup; supplied slots and cache'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    print(json.dumps(verify(parser.parse_args().executable),indent=2))
