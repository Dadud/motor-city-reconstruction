"""Compare native key schedule/block operation with standard DES.

Runs only original instructions under Unicorn, using synthetic keys and blocks.
Allocator/free boundaries are replaced by bounded emulator memory; no OS or
network services run. Requires optional cryptography in addition to Unicorn.
"""
import argparse
import json
import struct

from tools.native_oracle import DynoOracle


def verify(executable):
    from unicorn import UC_HOOK_CODE
    from cryptography.hazmat.primitives.ciphers import Cipher, modes
    from cryptography.hazmat.decrepit.ciphers.algorithms import TripleDES
    oracle = DynoOracle(executable)
    cpu, reg = oracle.cpu, oracle.reg
    cpu.mem_map(0, 4096)  # isolated SEH-chain slot, not host memory
    heap = oracle.inputs+0x4000
    emitted = []
    sink = oracle.inputs+0x3000
    sink_return, sink_write = oracle.stub+0x200, oracle.stub+0x210

    def memory(cpu, address, size, user):
        nonlocal heap
        if address in (sink_return, sink_write):
            stack = cpu.reg_read(reg.UC_X86_REG_ESP)
            target = struct.unpack('<I', cpu.mem_read(stack, 4))[0]
            if address == sink_return:
                cpu.reg_write(reg.UC_X86_REG_EAX, sink)
                cleanup = 4
            else:
                pointer, length = struct.unpack('<II', cpu.mem_read(stack+4, 8))
                if length != 8:
                    raise ValueError('unexpected CBC emission length')
                emitted.append(bytes(cpu.mem_read(pointer, length)))
                cleanup = 12
            cpu.reg_write(reg.UC_X86_REG_ESP, stack+cleanup)
            cpu.reg_write(reg.UC_X86_REG_EIP, target)
            return
        if address not in (0x699382, 0x6992c5):
            return
        stack = cpu.reg_read(reg.UC_X86_REG_ESP)
        target, argument = struct.unpack('<II', cpu.mem_read(stack, 8))
        if address == 0x699382:
            allocation = (argument+15)&~15
            if allocation > 4096 or heap+allocation > oracle.inputs+0x10000:
                raise ValueError('cipher allocation exceeds emulator boundary')
            cpu.mem_write(heap, bytes(allocation))
            cpu.reg_write(reg.UC_X86_REG_EAX, heap)
            heap += allocation
        cpu.reg_write(reg.UC_X86_REG_ESP, stack+4)
        cpu.reg_write(reg.UC_X86_REG_EIP, target)

    cpu.hook_add(UC_HOOK_CODE, memory)
    values = [(bytes.fromhex('133457799BBCDFF1'), bytes.fromhex('0123456789ABCDEF')),
              (bytes(8), bytes(8)), (bytes(range(8)), bytes(range(8,16)))]
    matched = 0
    chaining_cases = 0
    for key, block in values:
        # An eight-byte TripleDES key expands to K,K,K, equivalent to DES.
        context = Cipher(TripleDES(key*3), modes.ECB()).encryptor()
        encrypted = context.update(block)+context.finalize()
        for direction, source, expected in ((0, block, encrypted), (1, encrypted, block)):
            oracle._reset()
            obj, key_address = oracle.inputs, oracle.inputs+0x1000
            cpu.mem_write(obj, bytes(12))
            cpu.mem_write(key_address, key)
            cpu.reg_write(reg.UC_X86_REG_ECX, obj)
            stack = cpu.reg_read(reg.UC_X86_REG_ESP)
            cpu.mem_write(stack, struct.pack('<III', oracle.stop, key_address, direction))
            oracle._run(0x7ce230, oracle.stop, count=100000)
            oracle._reset()
            cpu.mem_write(key_address, source)
            cpu.reg_write(reg.UC_X86_REG_ECX, obj)
            stack = cpu.reg_read(reg.UC_X86_REG_ESP)
            output = oracle.inputs+0x2000
            cpu.mem_write(stack, struct.pack('<III', oracle.stop, key_address, output))
            oracle._run(0x7ce600, oracle.stop, count=100000)
            if bytes(cpu.mem_read(output, 8)) != expected:
                raise ValueError('original block cipher differs from DES')
            matched += 1
        # Rebuild forward schedule, then execute real CBC full/tail handlers.
        oracle._reset()
        cpu.reg_write(reg.UC_X86_REG_ECX, obj)
        cpu.mem_write(key_address, key)
        stack = cpu.reg_read(reg.UC_X86_REG_ESP)
        cpu.mem_write(stack, struct.pack('<III', oracle.stop, key_address, 0))
        oracle._run(0x7ce230, oracle.stop, count=100000)
        filter_obj, table, chain = oracle.inputs+0x800, oracle.inputs+0xa00, oracle.inputs+0xb00
        sink_table = oracle.inputs+0xc00
        cpu.mem_write(filter_obj, bytes(0x54))
        cpu.mem_write(table, bytes(0x100))
        cpu.mem_write(filter_obj+4, struct.pack('<I', table))
        cpu.mem_write(table+0x94, struct.pack('<I', sink_return))
        cpu.mem_write(filter_obj+0x34, struct.pack('<IIII', obj, 8, 8, chain))
        cpu.mem_write(chain, bytes(8))
        cpu.mem_write(sink, struct.pack('<I', sink_table))
        cpu.mem_write(sink_table+4, struct.pack('<I', sink_write))
        emitted.clear()
        chunks = [block, block, b'tail!']
        for chunk in chunks:
            oracle._reset()
            cpu.mem_write(key_address, chunk)
            cpu.reg_write(reg.UC_X86_REG_ECX, filter_obj)
            stack = cpu.reg_read(reg.UC_X86_REG_ESP)
            cpu.mem_write(stack, struct.pack('<III', oracle.stop, key_address, len(chunk)))
            oracle._run(0x7cefc0 if len(chunk) == 8 else 0x7cf010, oracle.stop, count=100000)
        context = Cipher(TripleDES(key*3), modes.CBC(bytes(8))).encryptor()
        expected = context.update(block*2+b'tail!'+bytes(3))+context.finalize()
        if b''.join(emitted) != expected:
            raise ValueError('original CBC chaining/tail differs')
        chaining_cases += 1
    return {'matched_block_cases': matched, 'matched_chaining_tail_cases': chaining_cases,
            'coverage': 'emulated DES primitive and CBC encryption/tail; no network'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    print(json.dumps(verify(parser.parse_args().executable), indent=2))
