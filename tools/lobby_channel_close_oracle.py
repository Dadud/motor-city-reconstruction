"""Bounded original channel-close cleanup and serialization with synthetic state.

Original 0x73ec30 and serializer execute. Registry lookup, local communication
cleanup, logoff, allocation, transport and reference release are substituted
capture boundaries. No Windows import, socket or actual close request executes.
"""
import argparse
import json
import struct

from client.lobby_channel_close import ChannelCloseRequest, native_close_arguments
from tools.native_oracle import DynoOracle


def verify(executable):
    from unicorn import UC_HOOK_CODE
    oracle = DynoOracle(executable)
    cpu, reg = oracle.cpu, oracle.reg
    # Original SEH setup executes against an emulator-owned empty FS:0 chain.
    cpu.mem_map(0,4096)
    registry, vtable = oracle.inputs, oracle.inputs + 0x1000
    holder, connection = oracle.inputs + 0x2000, oracle.inputs + 0x3000
    channel_registry, allocated = oracle.inputs + 0x4000, oracle.inputs + 0x5000
    lookup, release = oracle.stub + 0x8000, oracle.stub + 0x9000
    socket = 0x12345678
    state = {}

    def boundary(_cpu,address,_size,_user):
        stack = cpu.reg_read(reg.UC_X86_REG_ESP)
        return_address = struct.unpack('<I',cpu.mem_read(stack,4))[0]
        cleanup, result = 0, 0
        if address == lookup:
            args_address, output = struct.unpack('<II',cpu.mem_read(stack + 4,8))
            if cpu.reg_read(reg.UC_X86_REG_ECX) != registry:
                raise AssertionError('registry receiver differs')
            if bytes(cpu.mem_read(args_address,8)) != state['pair']:
                raise AssertionError('registry local argument pair differs')
            cpu.mem_write(output,struct.pack('<I',holder if state['found'] else 0))
            state['events'].append('lookup')
            cleanup, result = 8, int(state['found'])
        elif address == 0x743890:
            channel = struct.unpack('<I',cpu.mem_read(stack + 4,4))[0]
            if channel != state['channel'] or cpu.reg_read(reg.UC_X86_REG_ECX) != channel_registry:
                raise AssertionError('local cleanup arguments differ')
            state['events'].append('cleanup')
            cleanup, result = 4, state['cleanup_result']
        elif address == 0x699382:
            size = struct.unpack('<I',cpu.mem_read(stack + 4,4))[0]
            if size != 8: raise AssertionError('close serializer allocation differs')
            cpu.mem_write(allocated,b'\xa5' * 16)
            state['events'].append('allocate')
            result = allocated
        elif address == 0x736d90:
            packet, value_2, actual_socket, protocol, context, value_6 = struct.unpack('<6I',cpu.mem_read(stack + 4,24))
            if packet != allocated or (value_2,actual_socket,protocol,value_6) != (0,socket,0x21,1):
                raise AssertionError('transport arguments differ')
            # Fifth send argument references the retained connection holder;
            # it is distinct from the serializer's temporary header context.
            if struct.unpack('<I',cpu.mem_read(context,4))[0] != holder:
                raise AssertionError('transport connection holder differs')
            state['wire'] = bytes(cpu.mem_read(packet,8))
            state['events'].append('send')
            result = state['send_result']
        elif address == 0x73e2a0:
            selector = struct.unpack('<I',cpu.mem_read(stack + 4,4))[0]
            if selector != state['selector'] or cpu.reg_read(reg.UC_X86_REG_ECX) != registry:
                raise AssertionError('logoff boundary arguments differ')
            state['events'].append('logoff')
            cleanup = 4
        elif address == release:
            target = struct.unpack('<I',cpu.mem_read(stack + 4,4))[0]
            if target != holder + 4: raise AssertionError('reference-release pointer differs')
            state['events'].append('release')
            cleanup, result = 4, 1 # Retain supplied holder; destructor not exercised.
        cpu.reg_write(reg.UC_X86_REG_EAX,result)
        cpu.reg_write(reg.UC_X86_REG_ESP,stack + 4 + cleanup)
        cpu.reg_write(reg.UC_X86_REG_EIP,return_address)

    addresses = (lookup,0x743890,0x699382,0x736d90,0x73e2a0,release)
    hooks = [cpu.hook_add(UC_HOOK_CODE,boundary,begin=address,end=address) for address in addresses]
    matched = zero = missing = raw_cases = 0
    try:
        for selector in (0,1,44,0xffffffff):
            for channel in (1,0x12345678,0x80000000,0xffffffff,0):
                for found in (False,True):
                    for cleanup_result,send_result in ((0,0),(1,0xffffffff)):
                        oracle._reset()
                        state.clear()
                        state.update(selector=selector,channel=channel,found=found,
                            pair=native_close_arguments(selector,channel),events=[],
                            cleanup_result=cleanup_result,send_result=send_result)
                        cpu.mem_write(0,bytes(4))
                        cpu.mem_write(registry,struct.pack('<I',vtable))
                        cpu.mem_write(vtable + 0x14,struct.pack('<I',lookup))
                        cpu.mem_write(holder,bytes(16))
                        cpu.mem_write(holder + 8,struct.pack('<I',connection))
                        cpu.mem_write(connection,bytes(0x200))
                        cpu.mem_write(connection + 0x180,struct.pack('<I',channel_registry))
                        cpu.mem_write(connection + 0x16c,struct.pack('<I',socket))
                        cpu.mem_write(0x83b134,struct.pack('<I',release))
                        cpu.mem_write(0xb38014,bytes(4))
                        stack = cpu.reg_read(reg.UC_X86_REG_ESP)
                        cpu.mem_write(stack,struct.pack('<I',oracle.stop) + state['pair'])
                        cpu.reg_write(reg.UC_X86_REG_ECX,registry)
                        oracle._run(0x73ec30,oracle.stop,count=100000)
                        if not found:
                            expected = ['lookup']
                            missing += 1
                        elif channel == 0:
                            expected = ['lookup','logoff','release']
                            zero += 1
                        else:
                            expected = ['lookup','cleanup','allocate','send','release']
                            if state.get('wire') != ChannelCloseRequest(channel).frame().encode():
                                raise AssertionError('original channel close wire differs')
                            matched += 1
                        if state['events'] != expected:
                            raise AssertionError('channel close boundary order differs')
                        if bytes(cpu.mem_read(0,4)) != bytes(4):
                            raise AssertionError('original SEH chain not restored')
        # The generic builder permits zero as a raw uint32 field, although
        # normal public channel-close dispatch never takes that send branch.
        for channel in (0,1,0x12345678,0x80000000,0xffffffff):
            oracle._reset()
            state.clear()
            state['events'] = []
            source,context = oracle.inputs + 0x6000,oracle.inputs + 0x7000
            cpu.mem_write(source,struct.pack('<I',channel))
            cpu.mem_write(context,bytes(16))
            stack = cpu.reg_read(reg.UC_X86_REG_ESP)
            cpu.mem_write(stack,struct.pack('<3I',oracle.stop,0x105,source))
            cpu.reg_write(reg.UC_X86_REG_ECX,context)
            oracle._run(0x7e5e60,oracle.stop,count=100000)
            if cpu.reg_read(reg.UC_X86_REG_EAX) != allocated or state['events'] != ['allocate']:
                raise AssertionError('raw channel close builder boundary differs')
            if bytes(cpu.mem_read(allocated,8)) != ChannelCloseRequest(channel).frame().encode():
                raise AssertionError('raw original channel close serialization differs')
            raw_cases += 1
    finally:
        for hook in hooks: cpu.hook_del(hook)
    return {'matched_close_frames':matched,'matched_raw_serializer_cases':raw_cases,'verified_channel_zero_paths':zero,
            'verified_missing_registry_paths':missing,'original_serializer_executed':True,
            'substituted_boundaries':['registry lookup','local communication cleanup','allocator',
                'transport send','logoff','reference decrement'],
            'live_server_tested':False,'excluded':'real cleanup contents, I/O, transport result policy, holder destruction, server acknowledgement'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    print(json.dumps(verify(parser.parse_args().executable),indent=2))
