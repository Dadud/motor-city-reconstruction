"""Verify the original SHA-1 compression instructions with synthetic inputs.

Only the recovered compression routine is emulated. Padding, byte order, and
reference digests come from standard SHA-1; no session or networking is run.
"""
import argparse
import hashlib
import json
import struct

from tools.native_oracle import DynoOracle
from client.nps_crypto import encode_oaep_sha1, mask_sha1


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
    padding_cases = 0
    for size in (64, 128, 256):
        for message in (b'', b'x', b'x'*(size-42)):
            oracle._reset()
            data_address = oracle.inputs + 0x1000
            message_address = oracle.inputs + 0x2000
            stack = cpu.reg_read(reg.UC_X86_REG_ESP)
            # Entry begins after native allocation/lHash initialization. Supply
            # the recovered stack locals and execute only DB construction.
            cpu.mem_write(0xb44f40, hashlib.sha1(b'').digest())
            cpu.mem_write(message_address, message or b'\0')
            cpu.mem_write(stack+0x14, struct.pack('<I', size-21))
            cpu.mem_write(stack+0x54, struct.pack('<II', message_address, len(message)))
            cpu.reg_write(reg.UC_X86_REG_EBX, data_address)
            oracle._run(0x7c7b33, 0x7c7b82, count=10000)
            original = bytes(cpu.mem_read(data_address, size-21))
            seed = bytes(range(20))
            encoded = encode_oaep_sha1(message, size, seed)
            unmasked = bytes(a ^ b for a, b in zip(encoded[21:], mask_sha1(seed, size-21)))
            if original != unmasked:
                raise ValueError('original padding data block differs')
            padding_cases += 1
    return {'matched_hash_cases': len(values), 'matched_padding_cases': padding_cases,
            'coverage': 'emulated SHA-1 compression and padding data block; no RSA or network'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    print(json.dumps(verify(parser.parse_args().executable), indent=2))
