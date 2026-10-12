"""CPU-only comparison of the original login serializer against authored code.

Requires the exact external original executable and optional Unicorn package.
No executable entry point or network calls are run. htons/htonl boundaries are
replaced with their specified byte-swap results inside the emulator only.
"""
import argparse
import json
import random
import struct

from client.nps_login import LoginPayload
from tools.native_oracle import DynoOracle


def verify(executable, samples=40):
    from unicorn import UC_HOOK_CODE
    oracle = DynoOracle(executable)
    cpu, reg = oracle.cpu, oracle.reg

    def byte_swap(cpu, address, size, user):
        if address not in (0x749bec, 0x749c3a):
            return
        width = 2 if address == 0x749bec else 4
        stack = cpu.reg_read(reg.UC_X86_REG_ESP)
        result_address, value = struct.unpack('<II', cpu.mem_read(stack, 8))
        value &= (1 << (8*width)) - 1
        result = int.from_bytes(value.to_bytes(width, 'little'), 'big')
        cpu.reg_write(reg.UC_X86_REG_EAX, result)
        cpu.reg_write(reg.UC_X86_REG_ESP, stack + 8)
        cpu.reg_write(reg.UC_X86_REG_EIP, result_address)

    cpu.hook_add(UC_HOOK_CODE, byte_swap)
    randomizer = random.Random(501)
    values = [LoginPayload(b'', 0, b'', b'', 0),
              LoginPayload(b't'*128, 1, b'k'*512, b's'*64, 0xffffffff)]
    for _ in range(samples):
        def string(limit):
            return bytes(randomizer.randrange(1, 256)
                         for _ in range(randomizer.randrange(limit+1)))
        values.append(LoginPayload(string(128), randomizer.randrange(65536),
                                   string(512), string(64), randomizer.randrange(2**32)))
    for index, value in enumerate(values):
        oracle._reset()
        obj, output = oracle.inputs, oracle.inputs + 0x1000
        cpu.mem_write(obj, bytes(0x300))
        cpu.mem_write(obj + 0x10, struct.pack('<I', output))
        for offset, data in ((0x20, value.ticket), (0xa8, value.opaque_string),
                             (0x2a9, value.service_id)):
            cpu.mem_write(obj + offset, data + b'\0')
        cpu.mem_write(obj + 0xa4, struct.pack('<H', value.authorization_mode))
        cpu.mem_write(obj + 0x2ec, struct.pack('<I', value.caller_value))
        cpu.reg_write(reg.UC_X86_REG_ECX, obj)
        stack = cpu.reg_read(reg.UC_X86_REG_ESP)
        cpu.mem_write(stack, struct.pack('<I', oracle.stop))
        oracle._run(0x72c120, oracle.stop, count=100000)
        end = struct.unpack('<I', cpu.mem_read(obj + 0x10, 4))[0]
        actual = bytes(cpu.mem_read(output, end-output))
        if actual != value.encode():
            raise ValueError(f'original serializer differs in synthetic case {index}')
    return {'matched_cases': len(values), 'source': 'external original executable',
            'coverage': 'emulated payload serializer only; no network or authenticated login'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    args = parser.parse_args()
    print(json.dumps(verify(args.executable), indent=2))


if __name__ == '__main__':
    main()
