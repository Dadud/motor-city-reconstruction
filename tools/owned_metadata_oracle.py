"""Verify the original first metadata stores before text and physics enrichment."""
import argparse
import json
import struct
from client.owned_parts import OwnedPart, OwnedPartMetadata
from tools.native_oracle import DynoOracle


def verify(executable):
    oracle = DynoOracle(executable)
    cpu, reg = oracle.cpu, oracle.reg
    part = OwnedPart(42,123,17,9,0,500,200)
    for family in (0,10,26):
        metadata = OwnedPartMetadata(160001,200,1500,10000,1955,3,family,7,
                                     None,None,None,None,None)
        oracle._reset()
        cpu.mem_write(oracle.inputs,part.native_seed())
        for offset,value in ((-0x38,metadata.retail_price),(-0x44,metadata.part_type_id),
                (-0x30,metadata.max_item_wear),(-0x40,metadata.part_grade_id),
                (-0x3c,metadata.engine_block_family_id),(0xc,metadata.abstract_type_id)):
            cpu.mem_write(oracle.frame+offset,struct.pack('<i',value))
        cpu.mem_write(oracle.frame-0xd8,struct.pack('<h',metadata.manufacture_year))
        cpu.reg_write(reg.UC_X86_REG_EBX,oracle.inputs+0x1e3)
        cpu.reg_write(reg.UC_X86_REG_ESI,oracle.inputs)
        oracle._run(0x669346,0x669374,count=1000)
        if bytes(cpu.mem_read(oracle.inputs,1596)) != metadata.apply_numeric_fields(part):
            raise ValueError('original owned-part metadata stores differ')
    return {'matched_initial_metadata_cases':3,
            'scope':'initial numeric stores with query values supplied; text, physics and later pricing excluded'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    print(json.dumps(verify(parser.parse_args().executable),indent=2))
