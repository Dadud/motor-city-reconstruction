"""Verify original owned-instance field stores with controlled query values."""
import argparse
import json
import struct
from client.owned_parts import OwnedPart
from tools.native_oracle import DynoOracle


def verify(executable):
    oracle = DynoOracle(executable)
    cpu, reg = oracle.cpu, oracle.reg
    cases = (OwnedPart(42,123,17,9,0,500,200),
             OwnedPart(0xffffffff,0xfedcba98,-1,0x7fffffff,0xffffffff,-2147483648,0),
             OwnedPart(99,456,0,0,42,1,1))
    for part in cases:
        oracle._reset()
        output = oracle.inputs
        raw = bytearray(1596)
        struct.pack_into('<I',raw,0x5f8,part.part_id)
        cpu.mem_write(output,bytes(raw))
        for offset,value in ((-0x1c,part.branded_part_id),(-0x20,part.percent_damage),
                (-0x24,part.item_wear),(-0x28,part.parent_part_id),
                (-0x2c,part.repair_cost),(-0x30,part.scrap_value)):
            cpu.mem_write(oracle.frame+offset,struct.pack('<I',value & 0xffffffff))
        cpu.reg_write(reg.UC_X86_REG_ESI,output+0x5f8)
        # Original six stores only. Query binding, allocation, enrichment and
        # economy calculations are not executed in this controlled check.
        oracle._run(0x66f8eb,0x66f912,count=1000)
        if bytes(cpu.mem_read(output,1596)) != part.native_seed():
            raise ValueError('original owned-part instance fields differ')
    return {'matched_owned_part_seeds':len(cases),
            'scope':'six original field stores with query values substituted; no services'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    print(json.dumps(verify(parser.parse_args().executable),indent=2))
