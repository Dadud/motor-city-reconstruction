"""Complete original interface/result path and communication destructor guards.

Registry removal and host socket/critical-section boundaries are substituted.
No live socket or original PE entry point is invoked.
"""
import argparse
import itertools
import json
import random
import struct
from client.connection_disconnect import communication_socket_close_required, native_disconnect_result
from tools.native_oracle import DynoOracle


def verify(executable):
    from unicorn import UC_HOOK_CODE
    o = DynoOracle(executable)
    cpu, reg = o.cpu, o.reg
    cpu.mem_map(0, 0x1000)  # Inert x86 SEH chain; no exception handler runs.
    owner, registry = o.inputs, o.inputs + 0x2000
    delete_stub = o.stub + 0x100
    cpu.mem_write(0x83b278, struct.pack('<I', delete_stub))
    state = {}

    def boundary(_cpu, address, _size, _user):
        stack = cpu.reg_read(reg.UC_X86_REG_ESP)
        ret = struct.unpack('<I', cpu.mem_read(stack, 4))[0]
        cleanup = 0
        if address == 0x73e000:
            if cpu.reg_read(reg.UC_X86_REG_ECX) != registry:
                raise AssertionError('registry removal receiver differs')
            if struct.unpack('<I', cpu.mem_read(stack + 4, 4))[0] != state['id']:
                raise AssertionError('forwarded local connection ID differs')
            cpu.reg_write(reg.UC_X86_REG_EAX, state['removal'])
            cleanup = 4
        elif address == 0x7e2260:
            if struct.unpack('<I', cpu.mem_read(stack + 4, 4))[0] != owner + 0x34:
                raise AssertionError('socket-field pointer differs')
            state['calls'].append('close_socket')
            cleanup = 4
        elif address == 0x7e1bc0:
            state['calls'].append('transport_constructor')
        elif address == 0x7e1c40:
            state['calls'].append('transport_destructor')
        elif address == delete_stub:
            if struct.unpack('<I', cpu.mem_read(stack + 4, 4))[0] != owner + 0x3a4:
                raise AssertionError('deleted critical-section pointer differs')
            state['calls'].append('delete_critical_section')
            cleanup = 4
        cpu.reg_write(reg.UC_X86_REG_ESP, stack + 4 + cleanup)
        cpu.reg_write(reg.UC_X86_REG_EIP, ret)

    hooks = [cpu.hook_add(UC_HOOK_CODE, boundary, begin=a, end=a)
             for a in (0x73e000, 0x7e2260, 0x7e1bc0, 0x7e1c40, delete_stub)]
    rng = random.Random(0x743e40)
    result_cases = close_cases = 0
    try:
        cpu.mem_write(0xb38014, bytes(4))  # Logging disabled; no logger host effects.
        cpu.mem_write(0xb380d0, struct.pack('<I', registry))
        for removal, connection_id in itertools.product(
                (0, 1, 2, 0xffffffff), (0, 1, 7, 0x7fffffff, 0x80000000, 0xffffffff)):
            o._reset()
            stack = cpu.reg_read(reg.UC_X86_REG_ESP)
            cpu.mem_write(stack, struct.pack('<II', o.stop, connection_id))
            state.clear()
            state.update(removal=removal, id=connection_id)
            o._run(0x730b20, o.stop, count=1000)
            if cpu.reg_read(reg.UC_X86_REG_EAX) != native_disconnect_result(removal) & 0xffffffff:
                raise AssertionError('original disconnect interface result differs')
            result_cases += 1
        values = (0, 1, 7, 0x7fffffff, 0x80000000, 0xffffffff)
        for flag194, channel, flag19c in itertools.product(values, repeat=3):
            o._reset()
            image = bytearray(rng.randbytes(0x3bc))
            for offset, value in ((8, channel), (0x194, flag194), (0x19c, flag19c)):
                struct.pack_into('<I', image, offset, value)
            cpu.mem_write(owner, bytes(image))
            stack = cpu.reg_read(reg.UC_X86_REG_ESP)
            cpu.mem_write(stack, struct.pack('<I', o.stop))
            cpu.reg_write(reg.UC_X86_REG_ECX, owner)
            state.clear()
            state['calls'] = []
            o._run(0x743e40, o.stop, count=3000)
            calls = ['transport_constructor', 'close_socket', 'transport_destructor'] if (
                communication_socket_close_required(bytes(image))) else []
            if state['calls'] != calls + ['delete_critical_section']:
                raise AssertionError('original socket close guard/call order differs')
            struct.pack_into('<I', image, 0, 0x84b6b4)
            if bytes(cpu.mem_read(owner, len(image))) != bytes(image):
                raise AssertionError('original destructor image writes differ')
            close_cases += 1
    finally:
        for hook in hooks:
            cpu.hook_del(hook)
    return {'matched_complete_interface_result_cases': result_cases,
            'matched_complete_communication_destructor_cases': close_cases,
            'live_server_tested': False,
            'substitutions': ['registry removal73e000', 'transport construction/destruction',
                              'socket close helper', 'critical-section deletion'],
            'excluded': 'registry erase, reference ownership, actual socket state and concurrent execution'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    print(json.dumps(verify(parser.parse_args().executable), indent=2))
