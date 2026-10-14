"""Complete original room-disconnect control flow with scripted boundaries.

Only container reset, Sleep, enqueue, completion query and application pump are
substituted. Original branches, selective settings writes and return execute.
No unspecified task-tail bytes are interpreted or exported.
"""
import argparse
import json
import random
import struct
from client.room_disconnect import prepare_room_disconnect
from tools.native_oracle import DynoOracle


def observe(executable, room_image, *, wait_for_completion, pending_observations=(),
            completion_results=(), pump_results=(), operation_id=7, enqueue_return=0, _oracle=None):
    """Return original ordered calls, final image, enqueue image and signed result.

    Each pending observation is (pending uint32, connected uint16), applied by
    one Sleep(0) substitution. Each completion is None (absent) or signed int32.
    Pump returns are raw uint32; any nonzero result aborts the original loop.
    """
    from unicorn import UC_HOOK_CODE
    if not isinstance(room_image, bytes) or not 0x3ac <= len(room_image) <= 0xe000:
        raise ValueError('expected bounded room image')
    if type(wait_for_completion) is not bool or type(operation_id) is not int or not 1 <= operation_id <= 0xffffffff:
        raise ValueError('expected boolean wait and nonzero uint32 operation ID')
    if type(enqueue_return) is not int or not 0 <= enqueue_return <= 0xffffffff:
        raise ValueError('expected uint32 enqueue return')
    pending_observations = tuple(pending_observations)
    completion_results, pump_results = tuple(completion_results), tuple(pump_results)
    for pending, connected in pending_observations:
        if type(pending) is not int or not 0 <= pending <= 0xffffffff or type(connected) is not int or not 0 <= connected <= 0xffff:
            raise ValueError('invalid pending observation')
    for result in completion_results:
        if result is not None and (type(result) is not int or not -0x80000000 <= result <= 0x7fffffff):
            raise ValueError('invalid completion result')
    if any(type(result) is not int or not 0 <= result <= 0xffffffff for result in pump_results):
        raise ValueError('invalid pump result')
    o = _oracle or DynoOracle(executable)
    cpu, reg, owner = o.cpu, o.reg, o.inputs
    sleep_stub, pump_stub = o.stub + 0x100, o.stub + 0x110
    application, vtable = o.stub + 0x2000, o.stub + 0x2100
    o._reset()
    cpu.mem_write(owner, room_image)
    cpu.mem_write(0xb36a9c, bytes(4))
    cpu.mem_write(0x83b298, struct.pack('<I', sleep_stub))
    cpu.mem_write(0x892a3c, struct.pack('<I', application))
    cpu.mem_write(application, struct.pack('<I', vtable))
    cpu.mem_write(vtable + 4, struct.pack('<I', pump_stub))
    calls, enqueue_image = [], None
    consumed = {'pending': 0, 'completion': 0, 'pump': 0}
    record_pointer = None

    def boundary(_cpu, address, _size, _user):
        nonlocal enqueue_image, record_pointer
        stack = cpu.reg_read(reg.UC_X86_REG_ESP)
        ret = struct.unpack('<I', cpu.mem_read(stack, 4))[0]
        cleanup = 0
        if address in (0x4485f0, 0x456930):
            offset = 0x2e0 if address == 0x4485f0 else 0x1fc
            if cpu.reg_read(reg.UC_X86_REG_ECX) != owner + offset:
                raise AssertionError('container reset receiver differs')
            calls.append(('reset', offset))
        elif address == sleep_stub:
            if struct.unpack('<I', cpu.mem_read(stack + 4, 4))[0] != 0:
                raise AssertionError('pending sleep argument differs')
            index = consumed['pending']
            if index >= len(pending_observations):
                raise AssertionError('pending observation script exhausted')
            pending, connected = pending_observations[index]
            consumed['pending'] += 1
            calls.append(('sleep', 0))
            cpu.mem_write(owner + 0x3a8, struct.pack('<I', pending))
            cpu.mem_write(owner + 0xec, struct.pack('<H', connected))
            cleanup = 4
        elif address == 0x4a5390:
            if cpu.reg_read(reg.UC_X86_REG_ECX) != owner + 12:
                raise AssertionError('enqueue worker receiver differs')
            record_pointer, tracked = struct.unpack('<II', cpu.mem_read(stack + 4, 8))
            kind = struct.unpack('<I', cpu.mem_read(record_pointer, 4))[0]
            argument = bytes(cpu.mem_read(record_pointer + 12, 8))
            if tracked not in (0, 1):
                raise AssertionError('unexpected tracking argument')
            actual_id = operation_id if tracked else 0
            calls.append(('enqueue', kind, argument, bool(tracked), actual_id))
            enqueue_image = bytes(cpu.mem_read(owner, len(room_image)))
            cpu.mem_write(record_pointer + 4, struct.pack('<I', actual_id))
            cpu.reg_write(reg.UC_X86_REG_EAX, enqueue_return)
            cleanup = 8
        elif address == 0x4a5610:
            if cpu.reg_read(reg.UC_X86_REG_ECX) != owner + 12:
                raise AssertionError('completion worker receiver differs')
            query_id, output = struct.unpack('<II', cpu.mem_read(stack + 4, 8))
            if query_id != operation_id or output != record_pointer:
                raise AssertionError('completion ID/output pointer differs')
            index = consumed['completion']
            if index >= len(completion_results):
                raise AssertionError('completion script exhausted')
            result = completion_results[index]
            consumed['completion'] += 1
            calls.append(('query', query_id, result is not None))
            if result is not None:
                cpu.mem_write(output + 8, struct.pack('<i', result))
            cpu.reg_write(reg.UC_X86_REG_EAX, int(result is not None))
            cleanup = 8
        elif address == pump_stub:
            if cpu.reg_read(reg.UC_X86_REG_ECX) != application:
                raise AssertionError('application pump receiver differs')
            index = consumed['pump']
            if index >= len(pump_results):
                raise AssertionError('pump script exhausted')
            result = pump_results[index]
            consumed['pump'] += 1
            calls.append(('pump', result))
            cpu.reg_write(reg.UC_X86_REG_EAX, result)
        cpu.reg_write(reg.UC_X86_REG_ESP, stack + 4 + cleanup)
        cpu.reg_write(reg.UC_X86_REG_EIP, ret)

    hooks = [cpu.hook_add(UC_HOOK_CODE, boundary, begin=a, end=a)
             for a in (0x4485f0, 0x456930, sleep_stub, 0x4a5390, 0x4a5610, pump_stub)]
    try:
        stack = cpu.reg_read(reg.UC_X86_REG_ESP)
        cpu.mem_write(stack, struct.pack('<II', o.stop, wait_for_completion))
        cpu.reg_write(reg.UC_X86_REG_ECX, owner)
        o._run(0x44d750, o.stop, count=20000)
        raw_result = cpu.reg_read(reg.UC_X86_REG_EAX)
        return {'calls': tuple(calls), 'room_image': bytes(cpu.mem_read(owner, len(room_image))),
                'enqueue_image': enqueue_image,
                'result': raw_result if raw_result < 0x80000000 else raw_result - 0x100000000,
                'consumed': consumed}
    finally:
        for hook in hooks:
            cpu.hook_del(hook)


def _flow_observe(image, wait, pending_script, completions, pumps, operation_id):
    from client.room_disconnect_flow import RoomDisconnectFlow
    flow = RoomDisconnectFlow(image, wait_for_completion=wait)
    calls, enqueue_image = [], None
    pending_index = completion_index = pump_index = 0
    for _ in range(100):
        action = flow.action
        if action.kind == 'complete':
            return {'calls': tuple(calls), 'room_image': flow.room_image,
                    'enqueue_image': enqueue_image, 'result': action.result}
        if action.kind == 'reset_container':
            calls.append(('reset', action.owner_offset))
            flow.container_reset(flow.room_image)
        elif action.kind == 'yield_pending':
            calls.append(('sleep', 0))
            pending, connected = pending_script[pending_index]
            pending_index += 1
            observed = bytearray(flow.room_image)
            struct.pack_into('<I', observed, 0x3a8, pending)
            struct.pack_into('<H', observed, 0xec, connected)
            flow.pending_yielded(bytes(observed))
        elif action.kind == 'enqueue':
            if action.owner_offset != 12:
                raise AssertionError('controller enqueue receiver differs')
            calls.append(('enqueue', 1, action.argument, action.tracked,
                          operation_id if action.tracked else 0))
            enqueue_image = flow.room_image
            flow.enqueued(operation_id if action.tracked else None)
        elif action.kind == 'query_completion':
            if action.owner_offset != 12:
                raise AssertionError('controller query receiver differs')
            result = completions[completion_index]
            completion_index += 1
            calls.append(('query', action.operation_id, result is not None))
            flow.completion_queried(result)
        elif action.kind == 'pump_application':
            result = pumps[pump_index]
            pump_index += 1
            calls.append(('pump', result))
            flow.application_pumped(result if result < 0x80000000 else result - 0x100000000)
        else:
            raise AssertionError('unexpected controller action')
    raise AssertionError('controller did not complete bounded scenario')


def verify(executable):
    o = DynoOracle(executable)
    rng = random.Random(0x44d750)
    states = [(0, 0, ()), (0, 9, ()), (1, 0, ()),
              (1, 9, ((0, 1),)), (0xffff, 9, ((5, 0xffff), (2, 0xffff), (0, 0xffff))),
              (1, 9, ((8, 1), (0, 0))), (1, 9, ((8, 0), (0, 0)))]
    modes = [(False, (), (), 0),
             *[(True, (value,), (), value) for value in (-0x80000000, -51, -1, 0, 1, 0x7fffffff)],
             (True, (None, 0), (0,), 0), (True, (None, None, -7), (0, 0), -7),
             (True, (None,), (1,), -51), (True, (None, None), (0, 0x80000000), -51)]
    count = 0
    for connected, pending, pending_script in states:
        for wait, completions, pumps, expected_result in modes:
            for _ in range(4):
                image = bytearray(rng.randbytes(0x3c0))
                struct.pack_into('<H', image, 0xec, connected)
                struct.pack_into('<I', image, 0x3a8, pending)
                stable = bytearray(image)
                if connected and pending:
                    stable_pending, stable_connected = pending_script[-1]
                    struct.pack_into('<I', stable, 0x3a8, stable_pending)
                    struct.pack_into('<H', stable, 0xec, stable_connected)
                preparation = prepare_room_disconnect(bytes(stable), wait_for_completion=wait)
                operation_id = rng.choice((1, 7, 0x80000000, 0xffffffff))
                actual = observe(executable, bytes(image), wait_for_completion=wait,
                                 pending_observations=pending_script, completion_results=completions,
                                 pump_results=pumps, operation_id=operation_id, _oracle=o)
                controller = _flow_observe(bytes(image), wait, pending_script, completions, pumps, operation_id)
                if any(controller[key] != actual[key] for key in ('calls', 'room_image', 'enqueue_image', 'result')):
                    raise AssertionError('controller differs from original disconnect wait')
                calls = [('reset', 0x2e0), ('reset', 0x1fc)]
                if connected and pending:
                    calls.extend(('sleep', 0) for _ in pending_script)
                if preparation.argument is not None:
                    calls.append(('enqueue', 1, preparation.argument, wait, operation_id if wait else 0))
                    if actual['enqueue_image'] != preparation.room_image:
                        raise AssertionError('reset must precede enqueue')
                    if wait:
                        for index, result in enumerate(completions):
                            calls.append(('query', operation_id, result is not None))
                            if result is not None:
                                break
                            calls.append(('pump', pumps[index]))
                            if pumps[index] != 0:
                                break
                elif actual['enqueue_image'] is not None:
                    raise AssertionError('disconnected room unexpectedly enqueued')
                expected_return = expected_result if preparation.tracked else 0
                if actual['calls'] != tuple(calls) or actual['result'] != expected_return:
                    raise AssertionError('original wait call order/result differs')
                if actual['room_image'] != preparation.room_image:
                    raise AssertionError('original wait final room image differs')
                count += 1
    return {'matched_complete_disconnect_wait_cases': count,
            'matched_python_controller_cases': count,
            'live_server_tested': False,
            'substitutions': ['two container resets', 'Sleep(0)', 'enqueue', 'completion query', 'application pump'],
            'excluded': 'container effects, task bytes outside kind/initialized arguments, scheduling, threads and sockets'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    print(json.dumps(verify(parser.parse_args().executable), indent=2))
