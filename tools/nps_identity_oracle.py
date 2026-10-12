"""Compare executable checksum with bounded original instruction execution."""
import argparse
import json
import struct

from client.nps_identity import executable_checksum
from tools.native_oracle import DynoOracle


def verify(executable):
    oracle = DynoOracle(executable)
    cpu, reg = oracle.cpu, oracle.reg
    values = [b'', b'123456789', bytes(range(256)), b'x'*4096]
    for data in values:
        oracle._reset()
        cpu.mem_write(oracle.inputs, data or b'\0')
        stack = cpu.reg_read(reg.UC_X86_REG_ESP)
        cpu.mem_write(stack, struct.pack('<III', oracle.stop, len(data), oracle.inputs))
        oracle._run(0x658280, oracle.stop, count=100000)
        if cpu.reg_read(reg.UC_X86_REG_EAX) != executable_checksum(data):
            raise ValueError('authored checksum differs from original instructions')
    return {'matched_cases': len(values), 'coverage': 'emulated checksum routine; no server login'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    print(json.dumps(verify(parser.parse_args().executable), indent=2))
