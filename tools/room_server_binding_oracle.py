"""Bounded original task-zero connection-result writes and helper calls.

Connection interface, mini-room request helper and observer helper are explicit
substitutions. No authentication, queue or socket side effect is executed.
"""
import argparse
import json
import random
import struct

from client.room_server_binding import NETWORK_OWNER_MIN_SIZE, apply_server_connection_result
from tools.native_oracle import DynoOracle


def verify(executable):
    from unicorn import UC_HOOK_CODE
    oracle = DynoOracle(executable)
    cpu, reg = oracle.cpu, oracle.reg
    owner = oracle.inputs
    interface, vtable, task = owner + 0x1000, owner + 0x1100, owner + 0x1200
    connect_stub = oracle.stub + 0x100
    state = {}

    def boundary(_cpu, address, _size, _user):
        stack = cpu.reg_read(reg.UC_X86_REG_ESP)
        ret = struct.unpack('<I', cpu.mem_read(stack, 4))[0]
        cleanup = 0
        if address == connect_stub:
            if cpu.reg_read(reg.UC_X86_REG_ECX) != interface:
                raise AssertionError('connection interface receiver differs')
            if struct.unpack('<I', cpu.mem_read(stack + 4, 4))[0] != task + 12:
                raise AssertionError('connection argument pointer differs')
            cleanup = 4
            cpu.reg_write(reg.UC_X86_REG_EAX, state['result'] & 0xffffffff)
        elif address == 0x451860:
            if cpu.reg_read(reg.UC_X86_REG_ECX) != owner:
                raise AssertionError('mini-room helper owner differs')
            state['calls'].append('mini_room_list')
        elif address == 0x456b20:
            if cpu.reg_read(reg.UC_X86_REG_ECX) != owner + 0x4a0:
                raise AssertionError('observer receiver differs')
            state['notification'] = struct.unpack('<II', cpu.mem_read(stack + 4, 8))
            state['calls'].append('notification')
            cleanup = 8
        cpu.reg_write(reg.UC_X86_REG_ESP, stack + 4 + cleanup)
        cpu.reg_write(reg.UC_X86_REG_EIP, ret)

    hooks = [cpu.hook_add(UC_HOOK_CODE, boundary, begin=a, end=a)
             for a in (connect_stub, 0x451860, 0x456b20)]
    rng = random.Random(0x454d50)
    count = 0
    try:
        for result in (-0x80000000, -59, -51, -6, -1, 0, 1, 7, 44, 0x7fffffff):
            for _ in range(8):
                oracle._reset()
                original = bytearray(rng.randbytes(NETWORK_OWNER_MIN_SIZE + 23))
                # The dispatcher receives main+12; its interface field is +6cc.
                struct.pack_into('<I', original, 0x6d8, interface)
                cpu.mem_write(owner, bytes(original))
                cpu.mem_write(interface, struct.pack('<I', vtable))
                cpu.mem_write(vtable + 4, struct.pack('<I', connect_stub))
                cpu.mem_write(task, bytes(0x170))
                stack = cpu.reg_read(reg.UC_X86_REG_ESP)
                cpu.mem_write(stack, struct.pack('<II', oracle.stop, task))
                cpu.reg_write(reg.UC_X86_REG_ECX, owner + 12)
                state.clear()
                state.update(result=result, calls=[], notification=None)
                oracle._run(0x454d50, oracle.stop, count=10000)
                expected = apply_server_connection_result(bytes(original), result)
                if bytes(cpu.mem_read(owner, len(original))) != expected.owner_image:
                    raise AssertionError('original connection-result image differs')
                if cpu.reg_read(reg.UC_X86_REG_EAX) != result & 0xffffffff:
                    raise AssertionError('dispatcher return differs')
                calls = ['mini_room_list', 'notification'] if result >= 0 else []
                if state['calls'] != calls or state['notification'] != expected.notification:
                    raise AssertionError('success helper call sequence differs')
                count += 1
    finally:
        for hook in hooks:
            cpu.hook_del(hook)
    return {'matched_connection_binding_cases': count, 'live_server_tested': False,
            'substituted_boundaries': ['connection interface +4', 'mini room list451860', 'observer456b20'],
            'excluded': 'authentication, helper effects, queue execution and socket ownership'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    print(json.dumps(verify(parser.parse_args().executable), indent=2))
