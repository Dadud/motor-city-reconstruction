"""Bounded original channel wait lifecycle with explicit external boundaries.

Only synthetic state executes. Sleep, registry lookup, cancel callback and free
are captured substitutions; no wall-clock waiting, sockets or host imports run.
"""
import argparse
import json
import struct

from tools.native_oracle import DynoOracle
from client.lobby_channel_codec import ChannelReplyMailbox
from client.lobby_channel_wait import wait_for_channel_reply


def verify(executable):
    from unicorn import UC_HOOK_CODE
    oracle = DynoOracle(executable)
    cpu, reg = oracle.cpu, oracle.reg
    server, holder, wrapper = oracle.inputs, oracle.inputs + 0x1000, oracle.inputs + 0x1100
    argument, registry, vtable = oracle.inputs + 0x2000, oracle.inputs + 0x3000, oracle.inputs + 0x3100
    cancel_address, lookup_address = oracle.stub + 0x8000, oracle.stub + 0x9000
    pointer = oracle.inputs + 0x4000
    selector, callback_value = 0x12345678, 0x87654321
    cases = []

    def add(name, *, completion=None, nonnull=True, pending=None, cancel=None,
            callback=True, connected=True, disconnect_after=None, lookup_value=None, result=0,
            sleeps=1, lookups=1, callback_calls=1, freed=False, waiting=0,
            retained=False, completed=0):
        cases.append(dict(name=name, completion=completion, nonnull=nonnull,
                          pending=pending, cancel=cancel, callback=callback,
                          connected=connected, disconnect_after=disconnect_after, lookup_value=lookup_value,
                          result=result, sleeps=sleeps, lookups=lookups,
                          callback_calls=callback_calls, freed=freed,
                          waiting=waiting, retained=retained, completed=completed))

    for poll in (1,2,80):
        add(f'completed pointer at {poll}',completion=poll,sleeps=poll,lookups=poll,
            callback_calls=poll,retained=True,completed=1)
        add(f'completed null at {poll}',completion=poll,nonnull=False,result=-1,
            sleeps=poll,lookups=poll,callback_calls=poll,completed=1)
    add('timeout',result=-2,sleeps=81,lookups=81,callback_calls=80)
    add('timeout pending reply',pending=1,result=-2,sleeps=81,lookups=81,callback_calls=80,freed=True)
    add('completion on poll 81 loses to timeout',completion=81,result=-2,sleeps=81,
        lookups=81,callback_calls=80,freed=True,completed=1)
    add('disconnect overrides timeout',disconnect_after=80,result=-6,sleeps=81,
        lookups=81,callback_calls=80,waiting=1)
    add('disconnect overrides timeout preserves pending',pending=1,disconnect_after=80,
        result=-6,sleeps=81,lookups=81,callback_calls=80,waiting=1,retained=True)
    for pending in (None,1):
        add(f'cancel pending {pending}',pending=pending,cancel=1,result=-51,freed=pending is not None)
        add(f'disconnected cancel pending {pending}',pending=pending,cancel=1,connected=False,
            result=-6,waiting=1,retained=pending is not None)
        add(f'disconnected poll pending {pending}',pending=pending,connected=False,
            result=-6,waiting=1,retained=pending is not None)
    add('cancel beats completion',completion=1,cancel=1,result=-51,freed=True,completed=1)
    add('disconnect beats completion',completion=1,connected=False,result=-6,waiting=1,retained=True,completed=1)
    for value in (0,2,0xffffffff):
        add(f'callback value {value} does not cancel',completion=2,cancel=value,
            sleeps=2,lookups=2,callback_calls=2,retained=True,completed=1)
    add('no callback',completion=2,callback=False,sleeps=2,lookups=2,callback_calls=0,retained=True,completed=1)
    add('lookup AL zero despite nonzero EAX',lookup_value=0x100,result=-6,waiting=1)
    add('lookup AL nonzero',completion=1,lookup_value=0x101,retained=True,completed=1)

    state = {}
    def return_from_boundary(value, cleanup=0):
        stack = cpu.reg_read(reg.UC_X86_REG_ESP)
        return_address = struct.unpack('<I',cpu.mem_read(stack,4))[0]
        cpu.reg_write(reg.UC_X86_REG_EAX,value)
        cpu.reg_write(reg.UC_X86_REG_ESP,stack + 4 + cleanup)
        cpu.reg_write(reg.UC_X86_REG_EIP,return_address)

    def boundary(_cpu,address,_size,_user):
        case = state['case']
        stack = cpu.reg_read(reg.UC_X86_REG_ESP)
        supplied = struct.unpack('<I',cpu.mem_read(stack + 4,4))[0]
        if address == 0x7e3e50:
            state['trace'].append('sleep')
            if supplied != 0x3d090: raise AssertionError('sleep argument differs')
            state['sleeps'] += 1
            poll = state['sleeps']
            if poll == 1 and struct.unpack('<3I',cpu.mem_read(server + 0x18c,12)) != (0,0,1):
                raise AssertionError('wait initialization differs')
            if case['pending'] == poll: cpu.mem_write(server + 0x18c,struct.pack('<I',pointer))
            if case['completion'] == poll:
                cpu.mem_write(server + 0x18c,struct.pack('<II',pointer if case['nonnull'] else 0,1))
            return_from_boundary(0)
        elif address == cancel_address:
            state['trace'].append('cancel')
            if supplied != callback_value: raise AssertionError('callback argument differs')
            state['callback_calls'] += 1
            return_from_boundary(case['cancel'] if case['cancel'] is not None else 0)
        elif address == lookup_address:
            state['trace'].append('lookup')
            if cpu.reg_read(reg.UC_X86_REG_ECX) != registry: raise AssertionError('registry this pointer differs')
            if struct.unpack('<I',cpu.mem_read(supplied,4))[0] != selector:
                raise AssertionError('registry selector differs')
            state['lookups'] += 1
            connected = case['connected'] and (case['disconnect_after'] is None
                or state['lookups'] <= case['disconnect_after'])
            value = case['lookup_value'] if case['lookup_value'] is not None else int(connected)
            return_from_boundary(value,cleanup=4)
        elif address == 0x6992c5:
            state['trace'].append('free')
            if supplied != pointer: raise AssertionError('free pointer differs')
            if struct.unpack('<I',cpu.mem_read(server + 0x194,4))[0] != 0:
                raise AssertionError('waiting flag not cleared before free')
            state['free_calls'] += 1
            return_from_boundary(0)

    hooks = [cpu.hook_add(UC_HOOK_CODE,boundary,begin=address,end=address)
             for address in (0x7e3e50,cancel_address,lookup_address,0x6992c5)]
    try:
        for case in cases:
            oracle._reset()
            state.clear()
            state.update(case=case,sleeps=0,lookups=0,callback_calls=0,free_calls=0,trace=[])
            cpu.mem_write(server,bytes(0x200))
            cpu.mem_write(server + 4,struct.pack('<I',selector))
            cpu.mem_write(server + 0x18c,struct.pack('<3I',0xdeadbeef,7,0))
            cpu.mem_write(holder,struct.pack('<I',wrapper))
            cpu.mem_write(wrapper + 8,struct.pack('<I',server))
            cpu.mem_write(argument,bytes(0x15c))
            cpu.mem_write(argument + 0x154,struct.pack('<II',cancel_address if case['callback'] else 0,callback_value))
            cpu.mem_write(registry,struct.pack('<I',vtable))
            cpu.mem_write(vtable + 0x10,struct.pack('<I',lookup_address))
            cpu.mem_write(0xb380d0,struct.pack('<I',registry))
            cpu.mem_write(0xb38014,bytes(4))
            stack = cpu.reg_read(reg.UC_X86_REG_ESP)
            cpu.mem_write(stack,struct.pack('<3I',oracle.stop,holder,argument))
            oracle._run(0x73a360,oracle.stop,count=100000)
            raw = cpu.reg_read(reg.UC_X86_REG_EAX)
            result = raw if raw < 0x80000000 else raw - 0x100000000
            actual_pointer,completed,waiting = struct.unpack('<3I',cpu.mem_read(server + 0x18c,12))
            expected_state = (case['result'],pointer if case['retained'] else 0,case['completed'],case['waiting'])
            if (result,actual_pointer,completed,waiting) != expected_state:
                raise AssertionError(f"{case['name']}: original result/state differs")
            actual_counts = tuple(state[key] for key in ('sleeps','lookups','callback_calls','free_calls'))
            expected_counts = (case['sleeps'],case['lookups'],case['callback_calls'],int(case['freed']))
            if actual_counts != expected_counts:
                raise AssertionError(f"{case['name']}: boundary call counts differ {actual_counts} vs {expected_counts}")
            mailbox = ChannelReplyMailbox()
            mailbox.reply,mailbox.completed,mailbox.waiting = object(),True,False
            reply = object()
            counts = dict(sleeps=0,lookups=0,callback_calls=0,free_calls=0,trace=[])
            def sleep(value):
                counts['trace'].append('sleep')
                if value != 0x3d090: raise AssertionError('portable sleep interval differs')
                counts['sleeps'] += 1
                poll = counts['sleeps']
                if poll == 1 and (mailbox.reply is not None or mailbox.completed or not mailbox.waiting):
                    raise AssertionError('portable wait initialization differs')
                if case['pending'] == poll: mailbox.reply = reply
                if case['completion'] == poll:
                    mailbox.reply = reply if case['nonnull'] else None
                    mailbox.completed = True
            def connected():
                counts['trace'].append('lookup')
                counts['lookups'] += 1
                value = case['connected'] and (case['disconnect_after'] is None
                    or counts['lookups'] <= case['disconnect_after'])
                return bool(case['lookup_value'] & 255) if case['lookup_value'] is not None else value
            def cancel():
                counts['trace'].append('cancel')
                counts['callback_calls'] += 1
                return case['cancel'] if case['cancel'] is not None else 0
            def release(value):
                counts['trace'].append('free')
                if value is not reply or mailbox.waiting:
                    raise AssertionError('portable release argument/waiting state differs')
                counts['free_calls'] += 1
            portable = wait_for_channel_reply(mailbox,sleep_microseconds=sleep,is_connected=connected,
                cancel=cancel if case['callback'] else None,release_reply=release)
            if (portable.code,portable.polls,mailbox.reply is reply,int(mailbox.completed),int(mailbox.waiting)) != (
                    result,state['sleeps'],bool(actual_pointer),completed,waiting):
                raise AssertionError(f"{case['name']}: portable result/state differs")
            if tuple(counts[key] for key in ('sleeps','lookups','callback_calls','free_calls')) != actual_counts:
                raise AssertionError(f"{case['name']}: portable boundary counts differ")
            if counts['trace'] != state['trace']:
                raise AssertionError(f"{case['name']}: portable boundary order differs")
    finally:
        for hook in hooks: cpu.hook_del(hook)
    return {'matched_wait_cases':len(cases),'substituted_boundaries':['sleep7e3e50','registry virtual lookup',
            'supplied cancellation callback','free6992c5'],'maximum_polls':81,'live_server_tested':False,
            'coverage':'original73a360 entry through return; synthetic reply injection; no real threads or clock'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    print(json.dumps(verify(parser.parse_args().executable),indent=2))
