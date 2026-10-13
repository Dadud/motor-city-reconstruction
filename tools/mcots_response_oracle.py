"""Compare bounded original completion routing and attachment error mapping."""
import argparse
import json
import struct
from client.mcots_framing import MCOTSFrame
from client.mcots_response import decode_completion, attachment_status
from tools.native_oracle import DynoOracle


def verify(executable):
    oracle = DynoOracle(executable)
    cpu, reg = oracle.cpu, oracle.reg
    for opcode in (0x65, 0x66, 0x107):
        oracle._reset()
        allocation, queue, node, payload = (oracle.inputs+offset for offset in (0, 0x1000, 0x2000, 0x3000))
        cpu.mem_write(allocation, bytes(20))
        cpu.mem_write(allocation+15, struct.pack('<I', 17))
        cpu.mem_write(0xb29f8c, struct.pack('<I', queue))
        cpu.mem_write(queue, struct.pack('<I', node))
        cpu.mem_write(node, struct.pack('<7I', 0, 0, 0x1b6, 0, 0, 17, 0))
        body = struct.pack('<HHI', opcode, 0x1b6, 0x83)
        cpu.mem_write(payload, body)
        stack = cpu.reg_read(reg.UC_X86_REG_ESP)
        cpu.mem_write(stack, struct.pack('<5I', oracle.stop, allocation, opcode, 99, payload))
        # Runs original lookup/dispatch, stops before attachment handler.
        oracle._run(0x65dcd0, 0x681d30, count=10000)
        args = struct.unpack('<4I', bytes(cpu.mem_read(cpu.reg_read(reg.UC_X86_REG_ESP)+4, 16)))
        expected = decode_completion(MCOTSFrame(17, 0, body), transaction_value=17, operation=0x1b6)
        if args != (allocation, opcode, int(expected.successful), payload):
            raise ValueError('native generic completion routing differs')
    codes = (0x6b, 0x7c, 0x82, 0x83, 0xba, 0xbb, 0xbc, 0x1b4, 0x65, 0, 999, 0xffffffff)
    for code in codes:
        oracle._reset()
        payload, output = oracle.inputs, oracle.inputs+0x1000
        body = struct.pack('<HHI', 0x66, 0x1b6, code)
        cpu.mem_write(payload, body)
        cpu.mem_write(output, bytes(4))
        cpu.mem_write(oracle.frame+0x10, struct.pack('<II', 0, payload))
        cpu.reg_write(reg.UC_X86_REG_EDI, output)
        cpu.reg_write(reg.UC_X86_REG_EBX, 0)
        # Stops upon entering the free routine, before it executes.
        oracle._run(0x681e11, 0x6992c5, count=1000)
        actual = struct.unpack('<I', bytes(cpu.mem_read(output, 4)))[0]
        expected = attachment_status(decode_completion(MCOTSFrame(17, 0, body),
                                      transaction_value=17, operation=0x1b6))
        if actual != expected:
            raise ValueError('native attachment status differs')
    return {'matched_generic_routes': 3, 'matched_attachment_statuses': len(codes),
            'scope': 'bounded native routing/error mapping; no key initialization or network I/O'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    print(json.dumps(verify(parser.parse_args().executable), indent=2))
