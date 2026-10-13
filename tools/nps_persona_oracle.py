"""Replay the original persona-map payload writer with synthetic account IDs."""
import argparse
import json
import struct
from client.nps_persona import encode_persona_maps_request
from tools.native_oracle import DynoOracle


def verify(executable):
    from unicorn import UC_HOOK_CODE
    oracle = DynoOracle(executable)
    cpu, reg = oracle.cpu, oracle.reg

    def swap(cpu, address, size, user):
        if address != 0x749c3a:
            return
        stack = cpu.reg_read(reg.UC_X86_REG_ESP)
        target, value = struct.unpack('<II', cpu.mem_read(stack, 8))
        cpu.reg_write(reg.UC_X86_REG_EAX, int.from_bytes(value.to_bytes(4, 'little'), 'big'))
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
    return {'matched_cases': 4, 'coverage': 'native payload writer; request opcode traced statically; no server test'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    print(json.dumps(verify(parser.parse_args().executable), indent=2))
