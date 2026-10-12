"""Verify the original SHA-1 compression instructions with synthetic inputs.

Only the recovered compression routine is emulated. Padding, byte order, and
reference digests come from standard SHA-1; no session or networking is run.
"""
import argparse
import hashlib
import json
import struct

from tools.native_oracle import DynoOracle


def verify(executable):
    oracle = DynoOracle(executable)
    cpu, reg = oracle.cpu, oracle.reg
    values = [b'', b'abc', b'a'*55, b'a'*56, b'a'*64, bytes(range(256)), b'z'*512]
    for value in values:
        state = (0x67452301, 0xefcdab89, 0x98badcfe, 0x10325476, 0xc3d2e1f0)
        padded = value + b'\x80'
        padded += b'\0' * ((56-len(padded)) % 64)
        padded += struct.pack('>Q', len(value)*8)
        for offset in range(0, len(padded), 64):
            oracle._reset()
            cpu.mem_write(oracle.inputs, struct.pack('<5I', *state))
            words = struct.unpack('>16I', padded[offset:offset+64])
            cpu.mem_write(oracle.inputs+0x100, struct.pack('<16I', *words))
            stack = cpu.reg_read(reg.UC_X86_REG_ESP)
            cpu.mem_write(stack, struct.pack('<III', oracle.stop,
                                           oracle.inputs, oracle.inputs+0x100))
            oracle._run(0x7d22e0, oracle.stop, count=100000)
            state = struct.unpack('<5I', cpu.mem_read(oracle.inputs, 20))
        if struct.pack('>5I', *state) != hashlib.sha1(value).digest():
            raise ValueError('original compression does not match SHA-1')
    return {'matched_cases': len(values),
            'coverage': 'emulated SHA-1 compression only; no session or network'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    print(json.dumps(verify(parser.parse_args().executable), indent=2))
