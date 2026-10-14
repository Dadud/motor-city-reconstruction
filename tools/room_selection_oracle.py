"""Bounded original 0x450830 settings selection, with supplied cache results.

Original name equality, initializer and field transfer execute. Only settings
cache lookup is substituted; no startup, thread or socket is run.
"""
import argparse
import itertools
import json
import random
import struct

from client.room_selection import initialize_room_settings, select_room
from tools.native_oracle import DynoOracle


def verify(executable):
    from unicorn import UC_HOOK_CODE
    oracle = DynoOracle(executable)
    cpu, reg = oracle.cpu, oracle.reg
    cpu.mem_map(0, 4096)  # Inert empty FS exception chain, not a host TEB.
    network, name_address = oracle.inputs, oracle.inputs + 0x2000
    room_address = network + 0xa0
    state = {}

    def lookup(_cpu, _address, _size, _user):
        stack = cpu.reg_read(reg.UC_X86_REG_ESP)
        ret, name, destination = struct.unpack('<3I', cpu.mem_read(stack, 12))
        if cpu.reg_read(reg.UC_X86_REG_ECX) != network + 0x458 or name != name_address:
            raise AssertionError('settings-cache lookup receiver/name differs')
        state['lookups'] += 1
        cached = state['cached']
        if cached is not None:
            cpu.mem_write(destination, cached)
        cpu.reg_write(reg.UC_X86_REG_EAX, int(cached is not None))
        cpu.reg_write(reg.UC_X86_REG_ESP, stack + 12)
        cpu.reg_write(reg.UC_X86_REG_EIP, ret)

    hook = cpu.hook_add(UC_HOOK_CODE, lookup, begin=0x44be10, end=0x44be10)
    rng = random.Random(0x450830)
    selections = initializers = 0
    try:
        for _ in range(24):
            oracle._reset()
            image = rng.randbytes(0x170)
            cpu.mem_write(network, image)
            cpu.reg_write(reg.UC_X86_REG_ECX, network)
            stack = cpu.reg_read(reg.UC_X86_REG_ESP)
            cpu.mem_write(stack, struct.pack('<I', oracle.stop))
            oracle._run(0x44a460, oracle.stop, count=10000)
            if bytes(cpu.mem_read(network, len(image))) != initialize_room_settings(image):
                raise AssertionError('original settings initialization differs')
            if cpu.reg_read(reg.UC_X86_REG_EAX) != network:
                raise AssertionError('initializer receiver return differs')
            initializers += 1
        for connected, pending, name, cache_hit, _ in itertools.product(
                (0, 1, 0xffff), (0, 1, 0xffffffff),
                (b'old', b'OLD', b'', b'x' * 31), (False, True), range(2)):
            oracle._reset()
            image = bytearray(rng.randbytes(0x3c0))
            image[0xa0:0xc0] = b'old\0' + rng.randbytes(28)
            struct.pack_into('<H', image, 0xec, connected)
            struct.pack_into('<I', image, 0x3a8, pending)
            cached = bytearray(rng.randbytes(0x15a))
            cached[:len(name) + 1] = name + b'\0'
            cached[0x30:0x40] = b'secondary\0' + rng.randbytes(6)
            struct.pack_into('<H', cached, 0x4c, 0xffff)
            cached = bytes(cached) if cache_hit else None
            state.update(cached=cached, lookups=0)
            prefix = rng.randbytes(0xa0)
            cpu.mem_write(network, prefix)
            cpu.mem_write(room_address, bytes(image))
            cpu.mem_write(name_address, name + b'\0')
            cpu.mem_write(0, bytes(4))
            cpu.reg_write(reg.UC_X86_REG_ECX, network)
            stack = cpu.reg_read(reg.UC_X86_REG_ESP)
            cpu.mem_write(stack, struct.pack('<II', oracle.stop, name_address))
            oracle._run(0x450830, oracle.stop, count=100000)
            expected = select_room(bytes(image), name, cached_settings=cached)
            if (cpu.reg_read(reg.UC_X86_REG_EAX) != expected.result or
                    bytes(cpu.mem_read(room_address, len(image))) != expected.room_image):
                raise AssertionError('original room selection/result differs')
            if state['lookups'] != int(not connected and not pending):
                raise AssertionError('active guard cache lookup differs')
            if bytes(cpu.mem_read(network, len(prefix))) != prefix or bytes(cpu.mem_read(0, 4)) != bytes(4):
                raise AssertionError('network prefix or exception chain changed')
            selections += 1
    finally:
        cpu.hook_del(hook)
    return {'matched_room_selections': selections, 'matched_settings_initializers': initializers,
            'substituted_boundaries': ['settings cache lookup 0x44be10'],
            'live_server_tested': False,
            'excluded': 'cache comparison/copy internals, settings discovery, unsafe strings, scheduling and sockets'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    print(json.dumps(verify(parser.parse_args().executable), indent=2))
