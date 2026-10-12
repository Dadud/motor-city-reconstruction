"""CPU-only original success-reader checks; uses synthetic responses only."""
import argparse
import json
import struct

from client.nps_response import LoginSuccess, SessionKeyRecord
from tools.native_oracle import DynoOracle


def verify(executable):
    from unicorn import UC_HOOK_CODE
    oracle = DynoOracle(executable)
    cpu, reg = oracle.cpu, oracle.reg

    def swaps(cpu, address, size, user):
        if address not in (0x749c34, 0x749c40, 0x749bec, 0x749c3a):
            return
        width = 2 if address in (0x749c34, 0x749bec) else 4
        stack = cpu.reg_read(reg.UC_X86_REG_ESP)
        target, value = struct.unpack('<II', cpu.mem_read(stack, 8))
        value &= (1 << (width*8)) - 1
        cpu.reg_write(reg.UC_X86_REG_EAX,
                      int.from_bytes(value.to_bytes(width, 'little'), 'big'))
        cpu.reg_write(reg.UC_X86_REG_ESP, stack+8)
        cpu.reg_write(reg.UC_X86_REG_EIP, target)

    cpu.hook_add(UC_HOOK_CODE, swaps)

    def counted(value):
        return struct.pack('>H', len(value)) + value

    checked = 0
    for capacity in (0, 1, 32):
        record = struct.pack('>III', 7, 1, 1234) + counted(b'n'*capacity) + counted(b'a') + counted(b'b')
        session = counted(bytes(range(capacity))) + struct.pack('>I', 0x12345678)
        wire = (struct.pack('>IIB', 42, 99, 2) + counted(record)*2 + counted(session)
                + struct.pack('>I', 88) + counted(b'end'))
        expected = LoginSuccess.decode(wire)
        oracle._reset()
        obj, source = oracle.inputs, oracle.inputs + 0x2000
        cpu.mem_write(obj, bytes(0x600))
        cpu.mem_write(obj+0x10, struct.pack('<I', source))
        for offset, table in ((0x20, 0x84b11c), (0x290, 0x84b11c), (0x50c, 0x84aed8)):
            cpu.mem_write(obj+offset, struct.pack('<I', table))
        cpu.mem_write(source, wire)
        cpu.reg_write(reg.UC_X86_REG_ECX, obj)
        stack = cpu.reg_read(reg.UC_X86_REG_ESP)
        cpu.mem_write(stack, struct.pack('<I', oracle.stop))
        oracle._run(0x72bf90, oracle.stop, count=100000)
        fields = struct.unpack('<II', cpu.mem_read(obj+0x500, 8))
        assert fields == (expected.user_id, expected.value_2)
        assert cpu.mem_read(obj+0x508, 1)[0] == expected.flag
        assert struct.unpack('<III', cpu.mem_read(obj+0x40, 12)) == (7, 1, 1234)
        assert bytes(cpu.mem_read(obj+0x4c, capacity)) == expected.authorization_1.name
        assert bytes(cpu.mem_read(obj+0x52c, capacity)) == expected.session.material
        assert struct.unpack('<I', cpu.mem_read(obj+0x550, 4))[0] == expected.session.value
        assert struct.unpack('<I', cpu.mem_read(obj+0x554, 4))[0] == expected.value_3
        assert bytes(cpu.mem_read(obj+0x558, 3)) == expected.text
        assert struct.unpack('<I', cpu.mem_read(obj+0x10, 4))[0] == source+len(wire)
        checked += 1
    key_cases = 0
    for size in (0, 1, 32):
        oracle._reset()
        obj, output = oracle.inputs, oracle.inputs+0x2000
        material = bytes(range(size))
        cpu.mem_write(obj, bytes(0x48))
        cpu.mem_write(obj+0x10, struct.pack('<I', output))
        cpu.mem_write(obj+0x20, material or b'\0')
        cpu.mem_write(obj+0x42, struct.pack('<H', size))
        cpu.mem_write(obj+0x44, struct.pack('<I', 0x12345678))
        cpu.reg_write(reg.UC_X86_REG_ECX, obj)
        stack = cpu.reg_read(reg.UC_X86_REG_ESP)
        cpu.mem_write(stack, struct.pack('<I', oracle.stop))
        oracle._run(0x71d6d0, oracle.stop, count=100000)
        actual = bytes(cpu.mem_read(output, size+6))
        if actual != SessionKeyRecord(material, 0x12345678).encode():
            raise ValueError('original key-record serializer differs')
        key_cases += 1
    return {'matched_response_cases': checked, 'matched_key_record_cases': key_cases,
            'coverage': 'emulated success reader and key-record serializer; no network'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    print(json.dumps(verify(parser.parse_args().executable), indent=2))
