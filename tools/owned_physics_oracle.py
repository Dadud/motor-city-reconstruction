"""Compare recovered physics checksums with bounded original CPU execution."""
import argparse
import json
import struct
from client.owned_physics import encode_owned_physics
from tools.native_oracle import DynoOracle


def verify_loader(executable):
    """Execute the full loader with only query/lifetime boundaries replaced."""
    from unicorn import UC_HOOK_CODE
    oracle = DynoOracle(executable)
    cpu, reg = oracle.cpu, oracle.reg
    variants = {}
    present = [True]
    requested = []

    def boundary(cpu,address,size,unused):
        stack = cpu.reg_read(reg.UC_X86_REG_ESP)
        ret = struct.unpack('<I',bytes(cpu.mem_read(stack,4)))[0]
        cleanup = 4
        if address == 0x67f530:
            column, flag = struct.unpack('<II',bytes(cpu.mem_read(stack+4,8)))
            if flag != 0 or column not in variants:
                raise ValueError('unexpected original physics query binding')
            requested.append(column)
            cpu.reg_write(reg.UC_X86_REG_EAX,variants[column])
            cleanup += 8
        elif address == 0x67f890:
            cpu.reg_write(reg.UC_X86_REG_EAX,int(present[0]))
        # Variant destruction and heap release are excluded. Original numeric
        # conversion, CRC and strncpy instructions still execute.
        cpu.reg_write(reg.UC_X86_REG_ESP,stack+cleanup)
        cpu.reg_write(reg.UC_X86_REG_EIP,ret)

    hooks = [cpu.hook_add(UC_HOOK_CODE,boundary,begin=a,end=a)
             for a in (0x67f530,0x67f890,0x64c360,0x6992c5)]
    matched = 0
    try:
        for count,nullable_header in ((0,False),(1,False),(17,True),(50,False)):
            row = dict(PartTypeID=200,Ordinal=None if nullable_header else 2,
                       StatusID=3,DutyRating=700,MaxItemWear=10000,Mass=13.125)
            row.update({f'Val{i}': i/7 if i <= count else None for i in range(1,51)})
            row.update({f'TextVal{i}': None for i in range(1,9)})
            row.update(TextVal2='',TextVal4='x'*40,TextVal8='caf\u00e9')
            columns = ['PartTypeID','Ordinal','StatusID','DutyRating','MaxItemWear','Mass']
            columns += [f'Val{i}' for i in range(1,51)]
            columns += [f'TextVal{i}' for i in range(1,9)]
            oracle._reset()
            variants.clear()
            requested.clear()
            for column in range(1,64):
                value = row[columns[column]]
                address = oracle.inputs+0x1000+column*16
                variant = bytearray(16)
                if value is None:
                    struct.pack_into('<H',variant,0,1)
                elif column < 5:
                    struct.pack_into('<H',variant,0,3)
                    struct.pack_into('<i',variant,8,value)
                elif column < 56:
                    struct.pack_into('<H',variant,0,5)
                    struct.pack_into('<d',variant,8,value)
                else:
                    text = oracle.inputs+0x3000+(column-56)*128
                    cpu.mem_write(text,value.encode('cp1252')+b'\0')
                    struct.pack_into('<H',variant,0,8)
                    struct.pack_into('<I',variant,8,text)
                cpu.mem_write(address,bytes(variant))
                variants[column] = address
            cpu.mem_write(oracle.inputs,b'Z'*496)
            stack = cpu.reg_read(reg.UC_X86_REG_ESP)
            cpu.mem_write(stack,struct.pack('<5I',oracle.stop,oracle.inputs+0x5000,
                                           oracle.inputs,200,0))
            oracle._run(0x67d900,oracle.stop)
            expected = encode_owned_physics(row,text_encoding='cp1252')
            if bytes(cpu.mem_read(oracle.inputs,496)) != expected:
                raise ValueError('original full physics record differs')
            expected_columns = list(range(1,6))+list(range(6,6+min(count+1,50)))+list(range(56,64))
            if requested != expected_columns or cpu.reg_read(reg.UC_X86_REG_EAX) != 1:
                raise ValueError('original physics loader query sequence differs')
            matched += 1
        present[0] = False
        oracle._reset()
        cpu.mem_write(oracle.inputs,b'Z'*496)
        stack = cpu.reg_read(reg.UC_X86_REG_ESP)
        cpu.mem_write(stack,struct.pack('<5I',oracle.stop,oracle.inputs+0x5000,
                                       oracle.inputs,200,0))
        oracle._run(0x67d900,oracle.stop)
        if bytes(cpu.mem_read(oracle.inputs,496)) != bytes(496):
            raise ValueError('missing original physics row must clear record')
    finally:
        for hook in hooks:
            cpu.hook_del(hook)
    return {'matched_full_record_cases':matched,'matched_missing_row_cases':1,
            'loader_scope':'full original loader with synthetic query variants; SQL and memory lifetime helpers excluded'}


def verify(executable):
    oracle = DynoOracle(executable)
    matched = 0
    for count in (0, 1, 17, 50):
        row = dict(PartTypeID=200, Ordinal=1, StatusID=3,
                   DutyRating=700, MaxItemWear=10000, Mass=13.125)
        row.update({f'Val{i}': i*1.125 if i <= count else None for i in range(1,51)})
        row.update({f'TextVal{i}': None for i in range(1,9)})
        encoded = encode_owned_physics(row,text_encoding='cp1252')
        buffer = struct.pack('<iii',200,700,10000)+encoded[16:20]+encoded[40:240]
        oracle._reset()
        oracle.cpu.mem_write(oracle.inputs,buffer)
        stack = oracle.frame-0x1000
        oracle.cpu.mem_write(stack,struct.pack('<III',oracle.stop,len(buffer),oracle.inputs))
        oracle._run(0x658280,oracle.stop)
        original = oracle.cpu.reg_read(oracle.reg.UC_X86_REG_EAX)
        if original != struct.unpack_from('<I',encoded,36)[0]:
            raise ValueError('original physics checksum differs')
        matched += 1
    return {'matched_checksum_cases':matched,**verify_loader(executable)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    print(json.dumps(verify(parser.parse_args().executable),indent=2))
