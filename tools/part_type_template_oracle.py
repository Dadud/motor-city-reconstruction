"""Verify bounded AbstractPartType cache stores and owned-part template copies."""
import argparse
import json
import struct
from client.part_type_templates import encode_part_type_template, apply_part_type_template
from tools.native_oracle import DynoOracle


def verify(executable):
    oracle = DynoOracle(executable)
    cpu, reg = oracle.cpu, oracle.reg
    for identifier in (101,20001,160001):
        row = dict(AbstractPartTypeID=identifier,ParentAbstractPartTypeID=20001,DependsOn=160001,
            ModifiedRule=3,PartPaired=1,BlockFamilyCompatibility=2,GarageCategory=4,
            RepairCostModifier=0.125,ScrapValueModifier=0.375,EAPT='Type Name',EUT='Units',
            PartFilename='partfile',SchematicPicname1='picture1',SchematicPicname2='picture2')
        expected = encode_part_type_template(row,text_encoding='cp1252')
        oracle._reset()
        cpu.mem_write(oracle.inputs,bytes(3192))
        cpu.mem_write(0xb1801c,struct.pack('<I',oracle.inputs))
        for displacement,key in ((-0x20,'AbstractPartTypeID'),(-0x24,'ParentAbstractPartTypeID'),
                (-0x28,'DependsOn'),(-0x18,'ModifiedRule'),(-0x1c,'PartPaired'),
                (-0x40,'BlockFamilyCompatibility'),(-0x48,'GarageCategory')):
            cpu.mem_write(oracle.frame+displacement,struct.pack('<i',row[key]))
        for displacement,key in ((-0x30,'RepairCostModifier'),(-0x38,'ScrapValueModifier')):
            cpu.mem_write(oracle.frame+displacement,struct.pack('<f',row[key]))
        for displacement,key in ((-0x114,'EAPT'),(-0x7c,'PartFilename'),
                (-0x88,'SchematicPicname1'),(-0x94,'SchematicPicname2'),(-0x314,'EUT')):
            cpu.mem_write(oracle.frame+displacement,row[key].encode('cp1252')+b'\0')
        cpu.reg_write(reg.UC_X86_REG_ESI,0)
        cpu.reg_write(reg.UC_X86_REG_EDX,0)
        cpu.reg_write(reg.UC_X86_REG_EBX,0xffffffff)
        oracle._run(0x64d096,0x64d1bb,count=100000)
        if bytes(cpu.mem_read(oracle.inputs+1596,1596)) != expected:
            actual = bytes(cpu.mem_read(oracle.inputs+1596,1596))
            raise ValueError(f'original abstract-type cache record differs: {struct.unpack_from("<8i",actual)} vs {struct.unpack_from("<8i",expected)}')

        # Execute the four real helper lookups and their stores.
        oracle._reset()
        table = oracle.inputs+0x8000
        cpu.mem_write(table,bytes(1596)+expected)
        cpu.mem_write(0xb18018,struct.pack('<II',2,table))
        initial = bytearray(b'Z'*1596)
        struct.pack_into('<i',initial,0,identifier)
        cpu.mem_write(oracle.inputs,bytes(initial))
        cpu.mem_write(oracle.frame+0xc,struct.pack('<i',identifier))
        cpu.mem_write(cpu.reg_read(reg.UC_X86_REG_ESP),struct.pack('<i',identifier))
        cpu.reg_write(reg.UC_X86_REG_EBX,oracle.inputs+0x1e3)
        oracle._run(0x669374,0x6693b4,count=100000)
        helper_expected = bytearray(initial)
        for offset in (0xc,0x10,0x18,0x1c):
            helper_expected[offset:offset+4] = expected[offset:offset+4]
        if bytes(cpu.mem_read(oracle.inputs,1596)) != bytes(helper_expected):
            raise ValueError('original abstract-type helper stores differ')

        # Copy modifiers, filename and schematic labels, skipping intervening
        # model-brand copies which are verified separately.
        oracle._reset()
        cpu.mem_write(oracle.inputs,bytes(helper_expected))
        cpu.mem_write(oracle.frame+0xc,struct.pack('<i',identifier))
        cpu.reg_write(reg.UC_X86_REG_EBX,oracle.inputs+0x1e3)
        oracle._run(0x669541,0x669591,count=100000)
        cpu.mem_write(oracle.frame-0x10,struct.pack('<I',table+1596))
        oracle._run(0x6695fb,0x66965a,count=100000)
        if bytes(cpu.mem_read(oracle.inputs,1596)) != apply_part_type_template(bytes(initial),expected):
            raise ValueError('original owned-part template copy differs')
    return {'matched_template_record_cases':3,'matched_helper_store_cases':3,
            'matched_owned_template_copy_cases':3,
            'scope':'supplied query values; native stores, lookups and copies; query execution and display formatting excluded'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    print(json.dumps(verify(parser.parse_args().executable),indent=2))
