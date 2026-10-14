"""Original counter instruction range and complete identity lookup comparison.

Critical-section calls are inert substitutions. Tree iteration and C-string
comparison execute unchanged. Synthetic entries are explicit ordered trees.
"""
import argparse
import json
import random
import struct
from client.connection_registry import (ConnectionRegistryEntry,
                                        allocate_connection_id, find_existing_connection)
from tools.native_oracle import DynoOracle


def verify(executable):
    from unicorn import UC_HOOK_CODE
    o = DynoOracle(executable)
    cpu, reg = o.cpu, o.reg
    registry, owner = o.inputs, o.inputs + 0x1000
    vtable, head, nil = o.inputs + 0x2000, o.inputs + 0x2100, o.inputs + 0x2200
    username, hostname = o.inputs + 0x2300, o.inputs + 0x2400
    lock, unlock = o.stub + 0x100, o.stub + 0x110
    calls = []

    def critical(_cpu, address, _size, _user):
        if cpu.reg_read(reg.UC_X86_REG_ECX) != registry:
            raise AssertionError('registry critical-section receiver differs')
        calls.append('lock' if address == lock else 'unlock')
        stack = cpu.reg_read(reg.UC_X86_REG_ESP)
        ret = struct.unpack('<I', cpu.mem_read(stack, 4))[0]
        cpu.reg_write(reg.UC_X86_REG_ESP, stack + 4)
        cpu.reg_write(reg.UC_X86_REG_EIP, ret)

    hooks = [cpu.hook_add(UC_HOOK_CODE, critical, begin=a, end=a) for a in (lock, unlock)]
    rng = random.Random(0x73df10)
    allocation_cases = lookup_cases = 0
    try:
        counters = [0, 1, 0x7fffffff, 0x80000000, 0xfffffffe, 0xffffffff]
        counters += [rng.getrandbits(32) for _ in range(58)]
        for counter in counters:
            o._reset()
            cpu.mem_write(0xb380d0, struct.pack('<I', registry))
            cpu.mem_write(registry, struct.pack('<I', vtable))
            cpu.mem_write(registry + 0x2c, struct.pack('<I', counter))
            cpu.mem_write(vtable + 0x24, struct.pack('<II', lock, unlock))
            cpu.reg_write(reg.UC_X86_REG_EBP, owner)
            calls.clear()
            o._run(0x73f0fb, 0x73f122, count=200)
            actual = (struct.unpack('<I', cpu.mem_read(owner + 4, 4))[0],
                      struct.unpack('<I', cpu.mem_read(registry + 0x2c, 4))[0])
            if actual != allocate_connection_id(counter) or calls != ['lock', 'unlock']:
                raise AssertionError('original counter allocation differs')
            allocation_cases += 1

        sets = [[], [ConnectionRegistryEntry(0, b'U\0', b'H\0', 80)],
                [ConnectionRegistryEntry(i, u, h, p) for i, u, h, p in
                 [(0, b'U\0', b'H\0', 80), (7, b'U\0', b'H\0', 81),
                  (44, b'u\0', b'H\0', 80), (0xffffffff, b'\0', b'\0', 0)]]]
        queries = [(u, h, p) for u in (b'U\0', b'u\0', b'\0', b'Unknown\0')
                   for h in (b'H\0', b'h\0', b'\0') for p in (0, 80, 81, 65535)]
        for entries in sets:
            for u, h, port in queries:
                o._reset()
                cpu.mem_write(registry, bytes(0x60))
                cpu.mem_write(registry, struct.pack('<I', vtable))
                cpu.mem_write(registry + 8, struct.pack('<I', head))
                cpu.mem_write(registry + 0x10, struct.pack('<I', len(entries)))
                cpu.mem_write(vtable + 0x24, struct.pack('<II', lock, unlock))
                cpu.mem_write(0xb380c8, struct.pack('<I', nil))
                nodes = [o.inputs + 0x3000 + i * 0x400 for i in range(len(entries))]
                cpu.mem_write(head, struct.pack('<III', nodes[0] if nodes else head,
                                               nodes[0] if nodes else nil,
                                               nodes[-1] if nodes else head))
                for i, entry in enumerate(entries):
                    node, ref, connection = nodes[i], nodes[i] + 0x40, nodes[i] + 0x80
                    cpu.mem_write(node, struct.pack('<6I', nil, head if i == 0 else nodes[i-1],
                                                    nodes[i+1] if i+1 < len(nodes) else nil,
                                                    entry.connection_id, ref, 0))
                    cpu.mem_write(ref + 8, struct.pack('<I', connection))
                    cpu.mem_write(connection, bytes(0x178))
                    cpu.mem_write(connection + 4, struct.pack('<I', entry.connection_id))
                    cpu.mem_write(connection + 8, entry.hostname)
                    cpu.mem_write(connection + 0x10c, entry.username)
                    cpu.mem_write(connection + 0x174, struct.pack('<I', entry.port))
                cpu.mem_write(username, u)
                cpu.mem_write(hostname, h)
                stack = cpu.reg_read(reg.UC_X86_REG_ESP)
                cpu.mem_write(stack, struct.pack('<4I', o.stop, username, hostname, port))
                cpu.reg_write(reg.UC_X86_REG_ECX, registry)
                calls.clear()
                o._run(0x73df10, o.stop, count=5000)
                expected = find_existing_connection(entries, u, h, port) & 0xffffffff
                if cpu.reg_read(reg.UC_X86_REG_EAX) != expected or calls != ['lock', 'unlock']:
                    raise AssertionError('original existing-connection lookup differs')
                lookup_cases += 1
    finally:
        for hook in hooks:
            cpu.hook_del(hook)
    return {'matched_counter_range_cases': allocation_cases,
            'matched_complete_lookup_cases': lookup_cases,
            'live_server_tested': False, 'substitutions': ['critical-section calls'],
            'excluded': 'connection constructor outside counter range, registry insertion, sockets and lifetime'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    print(json.dumps(verify(parser.parse_args().executable), indent=2))
