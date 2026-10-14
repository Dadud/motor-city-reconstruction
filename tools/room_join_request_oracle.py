"""Bounded original room argument production through worker enqueue boundary.

The two preceding local-container reset calls and worker enqueue are substituted
with explicit captures. Original string copies and argument writes execute.
No thread, socket, room join, queue allocation or original callback is invoked.
"""
import argparse
import json
import random
import struct

from client.room_join_request import RoomJoinInputs, build_room_join_argument
from tools.native_oracle import DynoOracle


def verify(executable):
    from unicorn import UC_HOOK_CODE
    oracle = DynoOracle(executable)
    cpu, reg = oracle.cpu, oracle.reg
    owner, password_address = oracle.inputs, oracle.inputs + 0x1000
    state = {}

    def boundary(_cpu,address,_size,_user):
        stack = cpu.reg_read(reg.UC_X86_REG_ESP)
        return_address = struct.unpack('<I',cpu.mem_read(stack,4))[0]
        if address in (0x456930,0x4485f0):
            expected = owner + (0x1fc if address == 0x456930 else 0x2e0)
            if cpu.reg_read(reg.UC_X86_REG_ECX) != expected:
                raise AssertionError('local reset receiver differs')
            state['resets'].append(address)
            cpu.reg_write(reg.UC_X86_REG_EAX,0)
            cpu.reg_write(reg.UC_X86_REG_ESP,stack + 4)
            cpu.reg_write(reg.UC_X86_REG_EIP,return_address)
        else:
            task, wait = struct.unpack('<II',cpu.mem_read(stack + 4,8))
            if cpu.reg_read(reg.UC_X86_REG_ECX) != owner + 12:
                raise AssertionError('worker subobject receiver differs')
            if struct.unpack('<I',cpu.mem_read(task,4))[0] != 0:
                raise AssertionError('producer did not enqueue room task zero')
            state['argument'] = bytes(cpu.mem_read(task + 12,0x15c))
            state['wait'] = wait
            # Stop exactly at the captured queue boundary; do not execute queue
            # allocation or the following wait/event-pump paths.
            cpu.reg_write(reg.UC_X86_REG_EIP,oracle.stop)

    hooks = [cpu.hook_add(UC_HOOK_CODE,boundary,begin=address,end=address)
             for address in (0x456930,0x4485f0,0x4a5390)]
    rng = random.Random(0x44cf80)
    cases = guards = callbacks = 0
    try:
        for name_length in (0,1,29,30,31):
            for password in (None,b'',b'p',b'p' * 16):
                for flag in (False,True):
                    for wait in (False,True):
                        oracle._reset()
                        state.clear()
                        state['resets'] = []
                        image = bytearray(rng.randbytes(0x3b8))
                        image[0xa0:0xc0] = b'n' * name_length + bytes(32 - name_length)
                        struct.pack_into('<H',image,0xec,0)
                        struct.pack_into('<I',image,0x39c,rng.randrange(1,0x100000000))
                        struct.pack_into('<I',image,0x3a8,0)
                        cpu.mem_write(owner,bytes(image))
                        cpu.mem_write(password_address,(password or b'') + b'\0')
                        cpu.mem_write(0xb36a9c,bytes(4))
                        stack = cpu.reg_read(reg.UC_X86_REG_ESP)
                        # Poison locals to prove the producer's argument clearing.
                        cpu.mem_write(stack - 0x900,b'\xa5' * 0x900)
                        cpu.mem_write(stack,struct.pack('<4I',oracle.stop,int(wait),int(flag),
                                                       password_address if password is not None else 0))
                        cpu.reg_write(reg.UC_X86_REG_ECX,owner)
                        oracle._run(0x44cf80,oracle.stop,count=100000)
                        inputs = RoomJoinInputs.from_room_image(bytes(image))
                        expected = build_room_join_argument(inputs,password=password,flag_0x20=flag,
                            wait_for_completion=wait,owner_token=owner if wait else None)
                        if state.get('argument') != expected or state.get('wait') != int(wait):
                            raise AssertionError('original room argument or enqueue wait flag differs')
                        if state['resets'] != [0x456930,0x4485f0]:
                            raise AssertionError('local reset order differs')
                        if struct.unpack('<3I',cpu.mem_read(owner + 0x3a0,12)) != (0,0,1):
                            raise AssertionError('producer pending/result fields differ')
                        cases += 1
        for connected,busy,server,name,expected_result in (
                (1,0,44,b'room',0),(0,1,44,b'room',-1),(0,0,0,b'LOBBY',-1)):
            oracle._reset()
            state.clear()
            state['resets'] = []
            image = bytearray(0x3b8)
            image[0xa0:0xa0 + len(name)] = name
            struct.pack_into('<H',image,0xec,connected)
            struct.pack_into('<I',image,0x3a8,busy)
            struct.pack_into('<I',image,0x39c,server)
            cpu.mem_write(owner,bytes(image))
            cpu.mem_write(0xb36a9c,bytes(4))
            stack = cpu.reg_read(reg.UC_X86_REG_ESP)
            cpu.mem_write(stack,struct.pack('<4I',oracle.stop,0,0,0))
            cpu.reg_write(reg.UC_X86_REG_ECX,owner)
            oracle._run(0x44cf80,oracle.stop,count=100000)
            result = cpu.reg_read(reg.UC_X86_REG_EAX)
            if result != expected_result & 0xffffffff or 'argument' in state or state['resets']:
                raise AssertionError('original producer guard differs')
            guards += 1
    finally:
        for hook in hooks: cpu.hook_del(hook)
    # The installed callback itself is tiny and executes without a host import.
    # These values confirm its raw return, not the upstream event-pump policy.
    for value in (0,1,2,0xffffffff):
        oracle._reset()
        cpu.mem_write(owner + 8,struct.pack('<I',value))
        stack = cpu.reg_read(reg.UC_X86_REG_ESP)
        cpu.mem_write(stack,struct.pack('<II',oracle.stop,owner))
        oracle._run(0x44d740,oracle.stop,count=100)
        if cpu.reg_read(reg.UC_X86_REG_EAX) != value:
            raise AssertionError('original cancellation callback return differs')
        callbacks += 1
    return {'matched_argument_producers':cases,'verified_guard_cases':guards,
            'matched_cancel_callback_cases':callbacks,'worker_task':0,'worker_this_adjustment':12,
            'substituted_boundaries':['local reset456930','local reset4485f0','worker enqueue4a5390'],
            'live_server_tested':False,'excluded':'actual queue allocation, worker execution, event pump, socket room joining'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    print(json.dumps(verify(parser.parse_args().executable),indent=2))
