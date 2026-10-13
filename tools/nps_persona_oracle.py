"""Replay the original persona-map payload writer with synthetic account IDs."""
import argparse
import json
import struct
from client.nps_persona import encode_persona_maps_request, PersonaMaps
from tools.native_oracle import DynoOracle


def verify(executable):
    from unicorn import UC_HOOK_CODE
    oracle = DynoOracle(executable)
    cpu, reg = oracle.cpu, oracle.reg

    def swap(cpu, address, size, user):
        if address not in (0x749c3a, 0x749c40, 0x749c34):
            return
        stack = cpu.reg_read(reg.UC_X86_REG_ESP)
        target, value = struct.unpack('<II', cpu.mem_read(stack, 8))
        width = 2 if address == 0x749c34 else 4
        value &= (1 << (width*8))-1
        cpu.reg_write(reg.UC_X86_REG_EAX, int.from_bytes(value.to_bytes(width, 'little'), 'big'))
        cpu.reg_write(reg.UC_X86_REG_ESP, stack+8)
        cpu.reg_write(reg.UC_X86_REG_EIP, target)

    cpu.hook_add(UC_HOOK_CODE, swap)
    for value in (1, 42, 0x12345678, 0xffffffff):
        oracle._reset()
        obj, output = oracle.inputs, oracle.inputs+0x1000
        cpu.mem_write(obj, bytes(0x24))
        cpu.mem_write(obj+0x10, struct.pack('<I', output))
        cpu.mem_write(obj+0x20, struct.pack('<I', value))
        cpu.reg_write(reg.UC_X86_REG_ECX, obj)
        stack = cpu.reg_read(reg.UC_X86_REG_ESP)
        cpu.mem_write(stack, struct.pack('<I', oracle.stop))
        oracle._run(0x71e340, oracle.stop, count=10000)
        if bytes(cpu.mem_read(output, 4)) != encode_persona_maps_request(value)[12:]:
            raise ValueError('native persona-map payload differs')
        if struct.unpack('<I', cpu.mem_read(obj+0x10, 4))[0] != output+4:
            raise ValueError('native writer did not advance by four bytes')
    entry_cases = 0
    for name in (b'', b'Motor City', b'n'*32):
        oracle._reset()
        obj, source = oracle.inputs, oracle.inputs+0x1000
        record = struct.pack('>4IH', 1, 0xffffffff, 3, 4, len(name))+name
        payload = b'\0\1'+struct.pack('>H', len(record))+record+b'\xff'
        expected = PersonaMaps.decode(payload).entries[0]
        cpu.mem_write(obj, bytes(0x54))
        cpu.mem_write(obj+0x10, struct.pack('<I', source))
        cpu.mem_write(source, record)
        cpu.reg_write(reg.UC_X86_REG_ECX, obj)
        stack = cpu.reg_read(reg.UC_X86_REG_ESP)
        cpu.mem_write(stack, struct.pack('<I', oracle.stop))
        oracle._run(0x71e820, oracle.stop, count=10000)
        values = struct.unpack('<4I', cpu.mem_read(obj+0x20, 16))
        if values != (expected.value_1, expected.value_2, expected.value_3, expected.value_4):
            raise ValueError('native persona map values differ')
        if bytes(cpu.mem_read(obj+0x30, len(name)+1)) != expected.name+b'\0':
            raise ValueError('native persona map name differs')
        if struct.unpack('<I', cpu.mem_read(obj+0x10, 4))[0] != source+len(record):
            raise ValueError('native persona map cursor differs')
        entry_cases += 1
    return {'matched_cases': 4, 'matched_entry_cases': entry_cases,
            'coverage': 'native request payload writer and response entry reader; outer list traced statically; no server test'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    print(json.dumps(verify(parser.parse_args().executable), indent=2))
