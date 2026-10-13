"""Compare recovered physics checksums with bounded original CPU execution."""
import argparse
import json
import struct
from client.owned_physics import encode_owned_physics
from tools.native_oracle import DynoOracle


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
    return {'matched_checksum_cases':matched,
            'scope':'original checksum routine; query loading and record placement excluded'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    print(json.dumps(verify(parser.parse_args().executable),indent=2))
