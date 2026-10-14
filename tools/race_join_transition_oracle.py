"""Complete original 5e7ba0 callback branches with explicit inert boundaries."""
import argparse
import json
import struct
from client.race_join_transition import derive_race_join_transition
from tools.native_oracle import DynoOracle


def verify(executable):
    from unicorn import UC_HOOK_CODE
    o = DynoOracle(executable)
    cpu, reg = o.cpu, o.reg
    cpu.mem_map(0, 0x1000)
    callback, root, network, record = o.inputs, o.inputs + 0x1000, o.inputs + 0x2000, o.inputs + 0x4000
    vtable, disconnect_stub = o.stub + 0x2000, o.stub + 0x100
    state = {}

    def boundary(_cpu, address, _size, _user):
        stack = cpu.reg_read(reg.UC_X86_REG_ESP)
        ret = struct.unpack('<I', cpu.mem_read(stack, 4))[0]
        receiver = cpu.reg_read(reg.UC_X86_REG_ECX)
        cleanup = 0
        if address == 0x74bed0:
            if receiver != callback or struct.unpack('<I', cpu.mem_read(stack + 4, 4))[0] != 3:
                raise AssertionError('callback state receiver/value differs')
            state['actions'].append('set_callback_state_3')
            return  # Observe entry; execute the original helper unchanged.
        if address == 0x5d96e0:
            if receiver != root or struct.unpack('<I', cpu.mem_read(stack + 4, 4))[0] != 123:
                raise AssertionError('callback context receiver/value differs')
            state['actions'].append('activate_callback_context')
            cleanup = 4
        elif address == 0x44a110:
            if receiver != network or struct.unpack('<I', cpu.mem_read(stack + 4, 4))[0] != record + 12:
                raise AssertionError('selected-event server setup receiver/name differs')
            state['actions'].append('connect_selected_event_server')
            cpu.reg_write(reg.UC_X86_REG_EAX, state['setup'] & 0xffffffff)
            cleanup = 4
        elif address == 0x450830:
            pointer = struct.unpack('<I', cpu.mem_read(stack + 4, 4))[0]
            if receiver != network + 0xdc0 or bytes(cpu.mem_read(pointer, 6)) != b'LOBBY\0':
                raise AssertionError('secondary lobby setting receiver/name differs')
            state['actions'].append('select_secondary_lobby')
            cleanup = 4
        elif address == 0x44cf80:
            if receiver != network + 0xe60 or struct.unpack('<III', cpu.mem_read(stack + 4, 12)) != (1, 0, 0):
                raise AssertionError('secondary lobby join receiver/options differ')
            state['actions'].append('join_secondary_lobby')
            cpu.reg_write(reg.UC_X86_REG_EAX, state['join'] & 0xffffffff)
            cleanup = 12
        elif address == disconnect_stub:
            if receiver != network + 0xdc0 or struct.unpack('<I', cpu.mem_read(stack + 4, 4))[0] != 0:
                raise AssertionError('secondary disconnect receiver/options differ')
            state['actions'].append('disconnect_secondary_server')
            cleanup = 4
        elif address == 0x754c60:
            if struct.unpack('<I', cpu.mem_read(stack + 4, 4))[0] != 0xb99:
                raise AssertionError('error title resource differs')
            cleanup = 4
        elif address == 0x5d9630:
            error, _title, translations = struct.unpack('<III', cpu.mem_read(stack + 4, 12))
            if receiver != root:
                raise AssertionError('error reporter receiver differs')
            error = error if error < 0x80000000 else error - 0x100000000
            state['reported_error'] = error
            actions = state['actions']
            is_join = 'join_secondary_lobby' in actions
            actions.append('report_join_error' if is_join else 'report_setup_error')
            expected = (0xffffffff, 0xb9a, 0x20b, 0xb9a, 0x20b, 0xb9a, 0, 0) if is_join else (
                0x20b, 0xb97, 0xffffffe4, 0xb97, 0xffffffff, 0xb97, 0, 0)
            if struct.unpack('<8I', cpu.mem_read(translations, 32)) != expected:
                raise AssertionError('error translation table differs')
            cleanup = 12
        elif address == 0x5e4fe0:
            if struct.unpack('<I', cpu.mem_read(stack + 4, 4))[0] != record:
                raise AssertionError('selected event global update argument differs')
            state['actions'].append('apply_selected_event_globals')
            cleanup = 0  # Caller cleans this free-function argument.
        elif address == 0x74f560:
            if receiver != callback:
                raise AssertionError('dialog result receiver differs')
            state['dialog_result'], zero = struct.unpack('<II', cpu.mem_read(stack + 4, 8))
            if zero != 0:
                raise AssertionError('dialog result secondary argument differs')
            state['actions'].append('finish_dialog')
            cleanup = 8
        cpu.reg_write(reg.UC_X86_REG_ESP, stack + 4 + cleanup)
        cpu.reg_write(reg.UC_X86_REG_EIP, ret)

    boundaries = (0x74bed0, 0x5d96e0, 0x44a110, 0x450830, 0x44cf80, disconnect_stub,
                  0x754c60, 0x5d9630, 0x5e4fe0, 0x74f560)
    hooks = [cpu.hook_add(UC_HOOK_CODE, boundary, begin=a, end=a) for a in boundaries]
    scenarios = [(False, None, None)]
    scenarios += [(True, value, None) for value in (-0x80000000, -51, -1)]
    scenarios += [(True, setup, join) for setup in (0, 1, 7, 0x7fffffff)
                  for join in (-0x80000000, -51, -1, 0, 1, 0x7fffffff)]
    count = 0
    try:
        for present, setup, join in scenarios:
            o._reset()
            cpu.mem_write(callback, bytes(0xd4))
            cpu.mem_write(callback + 4, struct.pack('<I', 123))
            cpu.mem_write(callback + 0x84, struct.pack('<I', record if present else 0))
            cpu.mem_write(0x9e1060, struct.pack('<I', root))
            cpu.mem_write(root + 0x424, struct.pack('<I', network))
            cpu.mem_write(network + 0xdc0, struct.pack('<I', vtable))
            cpu.mem_write(vtable + 8, struct.pack('<I', disconnect_stub))
            stack = cpu.reg_read(reg.UC_X86_REG_ESP)
            cpu.mem_write(stack, struct.pack('<II', o.stop, callback))
            state.clear()
            state.update(setup=setup, join=join, actions=[], reported_error=None)
            o._run(0x5e7ba0, o.stop, count=10000)
            expected = derive_race_join_transition(selected_record_present=present, setup_result=setup, join_result=join)
            if tuple(state['actions']) != expected.actions or state['reported_error'] != expected.reported_error or state['dialog_result'] != expected.dialog_result:
                raise AssertionError('original callback transition differs')
            if struct.unpack('<I', cpu.mem_read(callback + 0xd0, 4))[0] != 3:
                raise AssertionError('original callback state differs')
            count += 1
    finally:
        for hook in hooks:
            cpu.hook_del(hook)
    return {'matched_complete_callback_transition_cases': count, 'live_server_tested': False,
            'excluded': 'server setup, lobby selection/join effects, event globals, error UI and dialog delivery'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    print(json.dumps(verify(parser.parse_args().executable), indent=2))
