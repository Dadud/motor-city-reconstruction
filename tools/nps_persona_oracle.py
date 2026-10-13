"""Replay the original persona-map payload writer with synthetic account IDs."""
import argparse
import json
import struct
from client.nps_persona import (encode_persona_maps_request, PersonaMaps,
                               encode_persona_activation_request)
from tools.native_oracle import DynoOracle


def verify(executable):
    from unicorn import UC_HOOK_CODE
    oracle = DynoOracle(executable)
    cpu, reg = oracle.cpu, oracle.reg

    def swap(cpu, address, size, user):
        if address == 0x699382:
            stack = cpu.reg_read(reg.UC_X86_REG_ESP)
            target, requested = struct.unpack('<II', cpu.mem_read(stack, 8))
            if requested != 24:
                raise ValueError('unexpected activation message allocation')
            cpu.reg_write(reg.UC_X86_REG_EAX, oracle.inputs+0x1000)
            cpu.reg_write(reg.UC_X86_REG_ESP, stack+4)
            cpu.reg_write(reg.UC_X86_REG_EIP, target)
            return
        if address not in (0x749c3a, 0x749c40, 0x749c34, 0x749bec):
            return
        stack = cpu.reg_read(reg.UC_X86_REG_ESP)
        target, value = struct.unpack('<II', cpu.mem_read(stack, 8))
        width = 2 if address in (0x749c34, 0x749bec) else 4
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
    activation_cases = 0
    for values in ((1, 42, 44), (0, 0, 0), (0xffffffff, 0x12345678, 65536)):
        oracle._reset()
        obj, output = oracle.inputs, oracle.inputs+0x1000
        cpu.mem_write(obj, bytes(0x2c))
        cpu.mem_write(obj+0x10, struct.pack('<I', output))
        cpu.mem_write(obj+0x20, struct.pack('<3I', *values))
        cpu.reg_write(reg.UC_X86_REG_ECX, obj)
        stack = cpu.reg_read(reg.UC_X86_REG_ESP)
        cpu.mem_write(stack, struct.pack('<I', oracle.stop))
        oracle._run(0x7290d0, oracle.stop, count=10000)
        if bytes(cpu.mem_read(output, 12)) != encode_persona_activation_request(*values)[12:]:
            raise ValueError('native persona activation payload differs')
        if struct.unpack('<I', cpu.mem_read(obj+0x10, 4))[0] != output+12:
            raise ValueError('native activation writer cursor differs')
        oracle._reset()
        cpu.mem_write(obj, struct.pack('<I', 0x84b0b4))
        cpu.mem_write(obj+8, bytes(24))
        cpu.mem_write(obj+0x14, struct.pack('<H', 0x503))
        cpu.mem_write(obj+0x18, b'\x01')
        cpu.reg_write(reg.UC_X86_REG_ECX, obj)
        stack = cpu.reg_read(reg.UC_X86_REG_ESP)
        length_ptr = oracle.inputs+0x3000
        cpu.mem_write(stack, struct.pack('<II', oracle.stop, length_ptr))
        oracle._run(0x7e0800, oracle.stop, count=100000)
        length = struct.unpack('<H', cpu.mem_read(length_ptr, 2))[0]
        if bytes(cpu.mem_read(output, length)) != encode_persona_activation_request(*values):
            raise ValueError('native complete activation message differs')
        activation_cases += 1
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
    conversion_cases = 0
    for index, name in enumerate((b'', b'Motor City', b'n'*32)):
        oracle._reset()
        obj, output = oracle.inputs, oracle.inputs+0x1000
        count_ptr, output_ptr = oracle.inputs+0x4000, oracle.inputs+0x4010
        values = (0x12345678, 42, 44, 0xffffffff)
        cpu.mem_write(obj, bytes(0x54))
        cpu.mem_write(obj+0x20, struct.pack('<4I', *values))
        cpu.mem_write(obj+0x30, name+b'\0')
        cpu.mem_write(output, bytes(0x510*3))
        cpu.mem_write(count_ptr, struct.pack('<H', index))
        cpu.mem_write(output_ptr, struct.pack('<I', output))
        cpu.reg_write(reg.UC_X86_REG_ESI, obj)
        cpu.reg_write(reg.UC_X86_REG_EBX, count_ptr)
        cpu.reg_write(reg.UC_X86_REG_EBP, output_ptr)
        # Execute the original strncpy too, stopping before object destruction.
        oracle._run(0x71e12b, 0x71e172, count=10000)
        dest = output+index*0x510
        for offset, value in zip((0, 0x38, 0x50c, 0x2c), values):
            if struct.unpack('<I', cpu.mem_read(dest+offset, 4))[0] != value:
                raise ValueError('native persona identity conversion differs')
        if bytes(cpu.mem_read(dest+4, 32)) != name.ljust(32, b'\0'):
            raise ValueError('native persona name conversion differs')
        if struct.unpack('<H', cpu.mem_read(count_ptr, 2))[0] != index+1:
            raise ValueError('native persona record index differs')
        conversion_cases += 1
    return {'matched_cases': 4, 'matched_entry_cases': entry_cases,
            'matched_conversion_cases': conversion_cases,
            'matched_activation_cases': activation_cases,
            'matched_activation_full_message_cases': activation_cases,
            'coverage': 'native map payload, full activation message, entry reader, identity conversion; outer list and activation replies traced statically; no server test'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    print(json.dumps(verify(parser.parse_args().executable), indent=2))
