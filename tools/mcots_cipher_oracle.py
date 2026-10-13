"""Compare original MCOTS RC4 scheduling and streams without network calls."""
import argparse
import json
import struct
from client.mcots_cipher import MCOTSCipher
from tools.native_oracle import DynoOracle


def verify(executable):
    oracle = DynoOracle(executable)
    cpu, reg = oracle.cpu, oracle.reg
    case_count = 0
    for key in (bytes(16), bytes(range(16)), b'0123456789abcdef'):
        oracle._reset()
        obj, state, source, key_pointer = (oracle.inputs+offset for offset in (0, 0x1000, 0x2000, 0x3000))
        cpu.mem_write(obj, bytes(20))
        cpu.mem_write(obj+12, struct.pack('<I', state))
        cpu.mem_write(key_pointer, key)
        cpu.mem_write(oracle.frame-0x10, struct.pack('<I', obj))
        cpu.mem_write(oracle.frame+8, struct.pack('<II', key_pointer, 16))
        # Original permutation fill and KSA, including native accessor/swap.
        # Allocation and constructor setup are excluded.
        oracle._run(0x6fd386, 0x6fd46d, count=100000)
        cipher = MCOTSCipher(key)
        if bytes(cpu.mem_read(state, 256)) != bytes(cipher._state):
            raise ValueError('native RC4 scheduling differs')
        for payload in (b'', b'login record'*4, bytes(range(256))*3):
            oracle._reset()
            stack = cpu.reg_read(reg.UC_X86_REG_ESP)
            cpu.mem_write(source, payload)
            cpu.mem_write(stack, struct.pack('<III', oracle.stop, source, len(payload)))
            cpu.reg_write(reg.UC_X86_REG_ECX, obj+4)
            oracle._run(0x6fd820, oracle.stop, count=100000)
            if bytes(cpu.mem_read(source, len(payload))) != cipher.transform(payload):
                raise ValueError('native RC4 stream differs')
            if bytes(cpu.mem_read(state, 256)) != bytes(cipher._state):
                raise ValueError('native persistent RC4 state differs')
            if bytes(cpu.mem_read(obj+16, 2)) != bytes((cipher._i, cipher._j)):
                raise ValueError('native RC4 indices differ')
            case_count += 1
    return {'matched_key_schedules': 3, 'matched_stream_calls': case_count,
            'scope': 'bounded original RC4 instructions; no attachment or network I/O'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    print(json.dumps(verify(parser.parse_args().executable), indent=2))
