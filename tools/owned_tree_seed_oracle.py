"""Verify original discovered-child ID/type/attachment/filename stores."""
import argparse
import json
import struct
from types import SimpleNamespace
from client.owned_parts import OwnedInstanceCache
from client.owned_tree import discover_owned_tree
from tools.native_oracle import DynoOracle


def verify(executable):
    oracle = DynoOracle(executable)
    cpu,reg = oracle.cpu,oracle.reg
    for abstract,filename,attachment in ((1001,'chassis',10),(160001,None,None)):
        row = dict(PartID=2,ParentPartID=1,BrandedPartID=3,AttachmentPointID=attachment,
                   PercentDamage=0,ItemWear=0,RepairCost=0,ScrapValue=0)
        catalogue = SimpleNamespace(branded={3:dict(PartTypeID=4)},
            types={4:dict(AbstractPartTypeID=abstract,PartFilename=filename)})
        expected = discover_owned_tree(1,OwnedInstanceCache([row]),catalogue,text_encoding='cp1252').slots[1]
        oracle._reset()
        cpu.mem_write(oracle.inputs,bytes(3192))
        for displacement,value in ((8,oracle.inputs),(-0x34,2),(-0x38,abstract),(-0x28,attachment or 0)):
            cpu.mem_write(oracle.frame+displacement,struct.pack('<I',value))
        cpu.mem_write(oracle.frame-0x50,('' if filename is None else filename).encode('cp1252')+b'\0')
        cpu.reg_write(reg.UC_X86_REG_EBX,1)
        oracle._run(0x66f4d1,0x66f531,count=1000)
        if bytes(cpu.mem_read(oracle.inputs+1596,1596)) != expected:
            raise ValueError('original owned child seed differs')
    return {'matched_child_seed_cases':2,
            'scope':'original stores and string copy; supplied query values, traversal/SQL/finalization excluded'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    print(json.dumps(verify(parser.parse_args().executable),indent=2))
