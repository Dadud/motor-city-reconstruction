"""Compare complete original 0x450db0 with explicit worker/pump/cache boundaries.

No original entry point, queue implementation, socket or host callback executes.
Temporary settings initialization executes unchanged; log output is disabled.
"""
import argparse
import itertools
import json
import struct

from client.game_start_flow import GameStartFlow
from tools.native_oracle import DynoOracle


def verify(executable):
    from unicorn import UC_HOOK_CODE
    o = DynoOracle(executable)
    cpu, reg = o.cpu, o.reg
    cpu.mem_map(0, 4096)
    owner, application, vtable, pump_stub = o.inputs, o.stub + 0x2000, o.stub + 0x2100, o.stub + 0x2200
    state = {}

    def boundary(_cpu, address, _size, _user):
        stack = cpu.reg_read(reg.UC_X86_REG_ESP)
        ret = struct.unpack('<I', cpu.mem_read(stack, 4))[0]
        cleanup = 0
        if address == 0x4a5390:
            record, tracked = struct.unpack('<II', cpu.mem_read(stack + 4, 8))
            if cpu.reg_read(reg.UC_X86_REG_ECX) != owner + 12 or tracked != 1:
                raise AssertionError('start enqueue receiver/tracking differs')
            if struct.unpack('<I', cpu.mem_read(record, 4))[0] != 5:
                raise AssertionError('start task kind differs')
            state['record'] = record
            state['calls'].append(('enqueue', bytes(cpu.mem_read(record + 12, 8))))
            cpu.mem_write(record + 4, struct.pack('<I', state['id']))
            cpu.reg_write(reg.UC_X86_REG_EAX, 0)  # Consumers must use record ID.
            cleanup = 8
        elif address == 0x4a5610:
            operation_id, output = struct.unpack('<II', cpu.mem_read(stack + 4, 8))
            if cpu.reg_read(reg.UC_X86_REG_ECX) != owner + 12 or operation_id != state['id'] or output != state['record']:
                raise AssertionError('start query receiver/record ID/output differs')
            result = next(state['completions'])
            state['calls'].append(('query', operation_id, result))
            if result is not None:
                cpu.mem_write(output + 8, struct.pack('<i', result))
            cpu.reg_write(reg.UC_X86_REG_EAX, int(result is not None))
            cleanup = 8
        elif address == pump_stub:
            if cpu.reg_read(reg.UC_X86_REG_ECX) != application:
                raise AssertionError('application receiver differs')
            result = next(state['pumps'])
            state['pump_count'] += 1
            channel = (state['channel'] + state['pump_count']) & 0xffffffff
            cpu.mem_write(owner + 0x160, struct.pack('<I', channel))
            state['calls'].append(('pump', result, channel))
            cpu.reg_write(reg.UC_X86_REG_EAX, result & 0xffffffff)
        else:
            channel, output = struct.unpack('<II', cpu.mem_read(stack + 4, 8))
            if cpu.reg_read(reg.UC_X86_REG_ECX) != owner + 0x458:
                raise AssertionError('room cache receiver differs')
            expected_channel = (state['channel'] + state['pump_count']) & 0xffffffff
            if channel != expected_channel:
                raise AssertionError('room cache query did not reread channel')
            status = next(state['statuses'])
            state['calls'].append(('status', channel, status))
            if status is not None:
                cpu.mem_write(output + 0x44, bytes([status]))
            cpu.reg_write(reg.UC_X86_REG_EAX, int(status is not None))
            cleanup = 8
        cpu.reg_write(reg.UC_X86_REG_ESP, stack + 4 + cleanup)
        cpu.reg_write(reg.UC_X86_REG_EIP, ret)

    hooks = [cpu.hook_add(UC_HOOK_CODE, boundary, begin=a, end=a)
             for a in (0x4a5390, 0x4a5610, 0x44be30, pump_stub)]
    scenarios = [((r,), (), ()) for r in (-1, -51, -20, -0x80000000)]
    for result, statuses, delays in itertools.product((0, 1, 0x7fffffff),
            ((None,), (8,), (4,), (1, 4), (0, 255, 8)), range(3)):
        scenarios.append(((None,) * delays + (result,), statuses, (0,) * (delays + len(statuses))))
    scenarios += [((None,), (), (1,)), ((0,), (), (-1,)), ((0,), (1,), (0, -0x80000000))]
    matched = 0
    try:
        for operation_id, selector, channel in ((1, 0, 0), (7, 44, 123),
                (0x80000000, 0xffffffff, 0xffffffff), (0xffffffff, 7, 0x80000000)):
            for completions, statuses, pumps in scenarios:
                o._reset()
                image = bytearray(b'\xa5' * 0x600)
                struct.pack_into('<I', image, 0x5cc, selector)
                struct.pack_into('<I', image, 0x160, channel)
                cpu.mem_write(owner, bytes(image))
                cpu.mem_write(0, bytes(4))
                cpu.mem_write(0xb36a9c, bytes(4))
                cpu.mem_write(0x892a3c, struct.pack('<I', application))
                cpu.mem_write(application, struct.pack('<I', vtable))
                cpu.mem_write(vtable + 4, struct.pack('<I', pump_stub))
                state.clear()
                state.update(id=operation_id, channel=channel, pump_count=0, calls=[],
                             completions=iter(completions), statuses=iter(statuses), pumps=iter(pumps))
                cpu.reg_write(reg.UC_X86_REG_ECX, owner)
                stack = cpu.reg_read(reg.UC_X86_REG_ESP)
                cpu.mem_write(stack, struct.pack('<I', o.stop))
                o._run(0x450db0, o.stop, count=50000)
                raw = cpu.reg_read(reg.UC_X86_REG_EAX)
                actual = raw if raw < 0x80000000 else raw - 0x100000000
                flow = GameStartFlow(bytes(image))
                queries, lookups, pumping = iter(completions), iter(statuses), iter(pumps)
                calls, pump_count = [], 0
                for _ in range(100):
                    action = flow.action
                    if action.kind == 'complete':
                        break
                    if action.kind == 'enqueue_task_5':
                        calls.append(('enqueue', action.argument))
                        flow.enqueued(operation_id)
                    elif action.kind == 'query_completion':
                        result = next(queries)
                        calls.append(('query', action.operation_id, result))
                        flow.completion_queried(result)
                    elif action.kind == 'pump_application':
                        result = next(pumping)
                        pump_count += 1
                        observed = bytearray(flow.network_image)
                        new_channel = (channel + pump_count) & 0xffffffff
                        struct.pack_into('<I', observed, 0x160, new_channel)
                        calls.append(('pump', result, new_channel))
                        flow.application_pumped(result, observed_network_image=bytes(observed))
                    else:
                        status = next(lookups)
                        calls.append(('status', action.channel_id, status))
                        flow.room_status_queried(status)
                else:
                    raise AssertionError('controller did not terminate within script')
                if state['calls'] != calls or actual != flow.action.result:
                    raise AssertionError('original game-start order/result differs')
                if bytes(cpu.mem_read(owner, len(image))) != flow.network_image or bytes(cpu.mem_read(0, 4)) != bytes(4):
                    raise AssertionError('owner image or exception chain differs')
                matched += 1
    finally:
        for hook in hooks:
            cpu.hook_del(hook)
    return {'matched_complete_start_wait_cases': matched, 'live_server_tested': False,
            'boundaries': ['tracked enqueue', 'completion query', 'application pump', 'room settings lookup'],
            'excluded': 'queue/thread effects, task padding, room cache copy internals, log output and sockets'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    print(json.dumps(verify(parser.parse_args().executable), indent=2))
