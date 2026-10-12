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

    def memory(cpu, address, size, user):
        nonlocal heap
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
    return {'matched_cases': matched, 'coverage': 'emulated DES key schedule and block operation; no mode or network'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    print(json.dumps(verify(parser.parse_args().executable), indent=2))
