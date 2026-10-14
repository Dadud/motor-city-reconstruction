"""Bounded original global key construction and serialization; no network."""
import argparse
import json
import struct

from client.nps_response import SessionKeyRecord
from client.nps_session_request import LOGIN_KEY_RECORD_VALUE
from tools.native_oracle import DynoOracle


def verify(executable):
    from unicorn import UC_HOOK_CODE
    oracle = DynoOracle(executable)
    cpu, reg = oracle.cpu, oracle.reg
    substitutions = []

    def imports(cpu, address, size, unused):
        stack = cpu.reg_read(reg.UC_X86_REG_ESP)
        if address == 0x7e0670:
            # Header buffer construction is outside the embedded key fields.
            # Supply a neutral base object and preserve thiscall stack cleanup.
            target = struct.unpack('<I', cpu.mem_read(stack, 4))[0]
            obj = cpu.reg_read(reg.UC_X86_REG_ECX)
            cpu.mem_write(obj, bytes(0x20))
            cpu.reg_write(reg.UC_X86_REG_EAX, obj)
            cpu.reg_write(reg.UC_X86_REG_ESP, stack + 12)
            cpu.reg_write(reg.UC_X86_REG_EIP, target)
            substitutions.append('base header constructor 0x7e0670')
        elif address in (0x749bec, 0x749c3a):
            # Windows htons/htonl imports, represented by exact byte swaps.
            target, value = struct.unpack('<II', cpu.mem_read(stack, 8))
            width = 2 if address == 0x749bec else 4
            value &= (1 << (width * 8)) - 1
            cpu.reg_write(reg.UC_X86_REG_EAX,
                          int.from_bytes(value.to_bytes(width, 'little'), 'big'))
            cpu.reg_write(reg.UC_X86_REG_ESP, stack + 8)
            cpu.reg_write(reg.UC_X86_REG_EIP, target)

    cpu.hook_add(UC_HOOK_CODE, imports)
    checked = 0
    for poison in (0, 0x55, 0xff):
        oracle._reset()
        wrapper, record = 0xb37e80, 0xb37e84
        cpu.mem_write(wrapper, bytes([poison]) * 0x4c)
        stack = cpu.reg_read(reg.UC_X86_REG_ESP)
        cpu.mem_write(stack, struct.pack('<I', oracle.stop))
        oracle._run(0x72a6f0, oracle.stop, count=10000)
        assert struct.unpack('<I', cpu.mem_read(wrapper, 4))[0] == 0x84b0f0
        assert struct.unpack('<I', cpu.mem_read(record, 4))[0] == 0x84aed8
        assert bytes(cpu.mem_read(record + 0x20, 32)) == bytes(32)
        assert struct.unpack('<H', cpu.mem_read(record + 0x42, 2))[0] == 0
        assert struct.unpack('<I', cpu.mem_read(record + 0x44, 4))[0] == LOGIN_KEY_RECORD_VALUE
        for length in (0, 1, 32):
            # Supply the material/length just as the login branch does; the
            # constructor's trailing field is left untouched.
            material = bytes(range(length))
            output = oracle.inputs + 0x2000
            cpu.mem_write(record + 0x20, material or b'\0')
            cpu.mem_write(record + 0x42, struct.pack('<H', length))
            cpu.mem_write(record + 0x10, struct.pack('<I', output))
            cpu.reg_write(reg.UC_X86_REG_ECX, record)
            stack = oracle.frame - 0x1000
            cpu.reg_write(reg.UC_X86_REG_ESP, stack)
            cpu.mem_write(stack, struct.pack('<I', oracle.stop))
            oracle._run(0x71d6d0, oracle.stop, count=10000)
            actual = bytes(cpu.mem_read(output, length + 6))
            if actual != SessionKeyRecord(material, LOGIN_KEY_RECORD_VALUE).encode():
                raise ValueError('original initialized key record differs')
            checked += 1
    return {'matched_initialized_records': checked,
            'coverage': 'global wrapper constructor and key serializer; no RSA or network',
            'substitutions': sorted(set(substitutions)) + ['Windows htons/htonl byte swaps']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    print(json.dumps(verify(parser.parse_args().executable), indent=2))
