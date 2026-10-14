"""Execute original 0x44eba0 with synthetic room worker state and boundaries.

Logging is disabled. Virtual channel-add and helper 0x456ae0 are substituted;
no imports, sockets, task execution, credentials or original startup run.
"""
import argparse
import json
import random
import struct

from client.room_join_result import apply_room_join_result, room_join_call
from tools.native_oracle import DynoOracle


def verify(executable):
    from unicorn import UC_HOOK_CODE
    oracle = DynoOracle(executable)
    cpu, reg = oracle.cpu, oracle.reg
    base, argument = oracle.inputs, oracle.inputs + 0x1000
    interface, table, add_address = oracle.inputs + 0x2000, oracle.inputs + 0x2100, oracle.stub + 0x8000
    image_size = 0x3c0
    rng = random.Random(0x44eba0)
    state = {}

    def boundary(_cpu, address, _size, _user):
        stack = cpu.reg_read(reg.UC_X86_REG_ESP)
        ret = struct.unpack('<I', cpu.mem_read(stack, 4))[0]
        if address == add_address:
            supplied = struct.unpack('<3I', cpu.mem_read(stack + 4, 12))
            expected = state['call']
            if cpu.reg_read(reg.UC_X86_REG_ECX) != expected.interface_token:
                raise AssertionError('original room channel-add interface differs')
            if supplied != (argument, expected.caller_value_1, expected.caller_value_2):
                raise AssertionError('original room channel-add arguments differ')
            if bytes(cpu.mem_read(argument, 0x15c)) != expected.argument:
                raise AssertionError('original room argument bytes differ')
            if bytes(cpu.mem_read(base, image_size)) != state['image']:
                raise AssertionError('original room state changed before channel-add')
            state['events'].append('channel_add')
            cpu.reg_write(reg.UC_X86_REG_EAX, state['result'] & 0xffffffff)
            cleanup = 12
        elif address == 0x456ae0:
            expected = state['transition']
            notification = expected.notification
            if notification is None:
                raise AssertionError('original negative result notified completion')
            if cpu.reg_read(reg.UC_X86_REG_ECX) != base + notification.owner_offset:
                raise AssertionError('original notification owner base differs')
            supplied = struct.unpack('<2I', cpu.mem_read(stack + 4, 8))
            if supplied != (notification.correlation_value, notification.channel_value):
                raise AssertionError('original notification arguments differ')
            if bytes(cpu.mem_read(base, image_size)) != expected.worker_image:
                raise AssertionError('original writes before notification differ')
            state['events'].append('notification')
            cpu.reg_write(reg.UC_X86_REG_EAX, 0xdeadbeef)
            cleanup = 8
        else:
            raise AssertionError('unexpected original boundary')
        cpu.reg_write(reg.UC_X86_REG_ESP, stack + 4 + cleanup)
        cpu.reg_write(reg.UC_X86_REG_EIP, ret)

    hooks = [cpu.hook_add(UC_HOOK_CODE, boundary, begin=address, end=address)
             for address in (add_address, 0x456ae0)]
    values = [-0x80000000, -59, -51, -6, -5, -1, 0, 1, 2, 255, 32768, 0x7fffffff]
    cases = [(result, correlation) for result in values for correlation in (0, 1, 0xffffffff, 0x87654321)]
    cases += [(rng.randint(-0x80000000, 0x7fffffff), rng.getrandbits(32)) for _ in range(24)]
    positive = negative = 0
    try:
        for index, (result, correlation) in enumerate(cases):
            oracle._reset()
            image = bytearray(rng.randbytes(image_size))
            struct.pack_into('<I', image, 0x39c, correlation)
            first, second = (-1 & 0xffffffff, 1) if index % 2 == 0 else (rng.getrandbits(32), rng.getrandbits(32))
            struct.pack_into('<3I', image, 0x3ac, first, second, interface)
            supplied_argument = rng.randbytes(0x15c)
            expected = apply_room_join_result(bytes(image), result)
            state.clear()
            state.update(image=bytes(image), result=result, transition=expected,
                         call=room_join_call(bytes(image), supplied_argument), events=[])
            cpu.mem_write(base, bytes(image))
            cpu.mem_write(argument, supplied_argument)
            cpu.mem_write(interface, struct.pack('<I', table))
            cpu.mem_write(table + 8, struct.pack('<I', add_address))
            cpu.mem_write(0xb36a9c, bytes(4))
            cpu.reg_write(reg.UC_X86_REG_ECX, base)
            stack = cpu.reg_read(reg.UC_X86_REG_ESP)
            cpu.mem_write(stack, struct.pack('<2I', oracle.stop, argument))
            oracle._run(0x44eba0, oracle.stop, count=10000)
            actual = cpu.reg_read(reg.UC_X86_REG_EAX)
            actual = actual if actual < 0x80000000 else actual - 0x100000000
            if actual != expected.return_code or bytes(cpu.mem_read(base, image_size)) != expected.worker_image:
                raise AssertionError('original room result state/return differs')
            expected_events = ['channel_add'] + (['notification'] if result >= 0 else [])
            if state['events'] != expected_events:
                raise AssertionError('original room result boundary order differs')
            if result >= 0:
                positive += 1
            else:
                negative += 1
    finally:
        for hook in hooks:
            cpu.hook_del(hook)
    return dict(matched_room_result_cases=len(cases), nonnegative_cases=positive, negative_cases=negative,
        original_binary_executed=True, live_server_tested=False,
        coverage='original44eba0 entry through return, logging disabled, virtual channel-add and456ae0 substituted',
        compared_full_worker_images=True, compared_forwarded_arguments=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    print(json.dumps(verify(parser.parse_args().executable), indent=2))
