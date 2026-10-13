"""Compare original list-copy instructions, including odd-sized records."""
import argparse
import json
import struct
from client.mcots_data_response import MCOTSDataReply
from client.mcots_framing import MCOTSFrame
from tools.native_oracle import DynoOracle


def verify(executable):
    oracle = DynoOracle(executable)
    cpu, reg = oracle.cpu, oracle.reg
    matched = 0
    for request, opcode, stride, entry, stop, append in (
            (0x144,0x145,569,0x65f3a0,0x65f3d0,True),
            (0x16b,0x16c,516,0x65fbad,0x65fbce,False)):
        for count, previous in ((0,0),(1,0),(3,2)):
            oracle._reset()
            record_bytes = bytes((i*37+11)&255 for i in range(count*stride))
            payload = struct.pack('<HHB',opcode,count,1)+record_bytes
            parsed = MCOTSDataReply.from_frame(MCOTSFrame(7,0,payload),
                transaction_value=7, request_operation=request)
            source, result, output = oracle.inputs, oracle.inputs+0x1000, oracle.inputs+0x2000
            expected = bytearray(b'\xa5'*8192)
            offset = previous*stride if append else 0
            expected[offset:offset+len(record_bytes)] = b''.join(parsed.records)
            cpu.mem_write(source,payload)
            cpu.mem_write(result,struct.pack('<3I',0,previous,output))
            cpu.mem_write(output,b'\xa5'*8192)
            cpu.mem_write(oracle.frame+0x14,struct.pack('<I',source))
            cpu.reg_write(reg.UC_X86_REG_EBX,result)
            cpu.reg_write(reg.UC_X86_REG_ESI,count)
            cpu.reg_write(reg.UC_X86_REG_EAX,previous)
            # Stop immediately after byte copying, before status/publication,
            # duplicate removal, allocation or pending-list operations.
            oracle._run(entry,stop,count=10000)
            if bytes(cpu.mem_read(output,8192)) != bytes(expected):
                raise ValueError('original data copy differs from recovered offsets')
            matched += 1
    return {'matched_data_copy_cases':matched,
            'scope':'bounded copies only; 0x145 appends, 0x16c overwrites; no network I/O'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    print(json.dumps(verify(parser.parse_args().executable),indent=2))
