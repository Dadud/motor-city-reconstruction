"""Compare standalone unboosted core solver with a verified local original."""
import argparse
import json
from pathlib import Path
import struct
from client.cylinder_solver import solve_core_record
from tools.native_oracle import DynoOracle

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    parser.add_argument('record',type=Path)
    args=parser.parse_args()
    record=bytes.fromhex(json.loads(args.record.read_text())['input_hex'])
    expected=DynoOracle(args.executable).solver(record)
    actual=solve_core_record(record)
    differences=[]
    for offset in range(0xc4,0x2d8,4):
        if actual[offset:offset+4] != expected[offset:offset+4]:
            differences.append((hex(offset),struct.unpack_from('<f',actual,offset)[0],struct.unpack_from('<f',expected,offset)[0]))
    print(json.dumps(dict(record_equal=actual==expected,different_fields=len(differences),first_differences=differences[:10]),indent=2))
    if actual!=expected:
        raise SystemExit(1)

if __name__=='__main__':
    main()
