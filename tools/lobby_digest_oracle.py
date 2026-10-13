"""Verify native digest compression against standard MD5 with synthetic inputs."""
import argparse
import hashlib
import json
import struct
from tools.native_oracle import DynoOracle


def verify(executable):
    oracle = DynoOracle(executable)
    cpu, reg = oracle.cpu, oracle.reg
    values = [b'', b'abc', bytes(range(32)), b'x'*55, b'x'*56,
              bytes(range(64)), bytes(range(256))]
    for value in values:
        state = (0x67452301, 0xefcdab89, 0x98badcfe, 0x10325476)
        padded = value+b'\x80'
        padded += bytes((56-len(padded)) % 64)
        padded += struct.pack('<Q', len(value)*8)
        for offset in range(0, len(padded), 64):
            oracle._reset()
            cpu.mem_write(oracle.inputs, struct.pack('<4I', *state))
            cpu.mem_write(oracle.inputs+0x100, padded[offset:offset+64])
            stack = cpu.reg_read(reg.UC_X86_REG_ESP)
            cpu.mem_write(stack, struct.pack('<III', oracle.stop, oracle.inputs, oracle.inputs+0x100))
            oracle._run(0x7cd990, oracle.stop, count=100000)
            state = struct.unpack('<4I', cpu.mem_read(oracle.inputs, 16))
        if struct.pack('<4I', *state) != hashlib.md5(value, usedforsecurity=False).digest():
            raise ValueError('native digest compression differs from MD5')
    return {'matched_cases': len(values), 'coverage': 'native compression; caller padding traced statically; no server test'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    print(json.dumps(verify(parser.parse_args().executable), indent=2))
