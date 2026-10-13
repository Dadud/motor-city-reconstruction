"""Compare native MCOTS send-buffer preparation without executing socket I/O."""
import argparse
import json
import struct
from client.mcots_framing import MCOTSFrame
from tools.native_oracle import DynoOracle


def verify(executable):
    oracle = DynoOracle(executable)
    cpu, reg = oracle.cpu, oracle.reg
    cpu.mem_map(oracle.inputs+0x10000, 0x1000)
    cases = ((b'x', 0, 0), (b'x'*39, 0x12345678, 8),
             (b'x'*65526, 0xffffffff, 255))
    for payload, transaction, flags in cases:
        oracle._reset()
        allocation = oracle.inputs
        cpu.mem_write(allocation, bytes(20)+payload)
        cpu.mem_write(allocation+9, struct.pack('<HIIB', len(payload), 0, transaction, flags))
        stack = cpu.reg_read(reg.UC_X86_REG_ESP)
        cpu.mem_write(stack+0x1c, struct.pack('<I', allocation))
        # Stops before the native send loop at 0x6f7fb1.
        cpu.reg_write(reg.UC_X86_REG_EAX, allocation)
        oracle._run(0x6f7f90, 0x6f7fb1, count=100)
        pointer = cpu.reg_read(reg.UC_X86_REG_EBX)
        length = cpu.reg_read(reg.UC_X86_REG_ESI)
        actual = bytes(cpu.mem_read(pointer, length))
        if actual != MCOTSFrame(transaction, flags, payload).encode():
            raise ValueError('native MCOTS send-buffer differs')
    return {'matched_send_buffer_cases': len(cases),
            'scope': 'native buffer preparation; no compression, encryption or socket I/O'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    print(json.dumps(verify(parser.parse_args().executable), indent=2))
