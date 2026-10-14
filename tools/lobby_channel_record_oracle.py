"""Compare original channel constructor/copy instructions on synthetic images.

Only the host critical-section initializer is replaced with an inert RET 4;
original string-copy code executes. No socket or game startup is executed.
"""
import argparse
import json
import random
import struct

from client.lobby_channel_record import (CHANNEL_ALLOCATION_SIZE, CHANNEL_ARGUMENT_SIZE,
                                        initialize_channel_image, materialize_channel_record)
from tools.native_oracle import DynoOracle


def verify(executable):
    oracle = DynoOracle(executable)
    cpu, reg = oracle.cpu, oracle.reg
    # Substitute only InitializeCriticalSection, preserving all channel data.
    lock_stub = oracle.stub + 0xe000
    cpu.mem_write(lock_stub, b'\xc2\x04\x00')
    cpu.mem_write(0x83b27c, struct.pack('<I', lock_stub))
    rng = random.Random(743)
    cases = 0
    for flags in (0, 1, 2, 4, 5, 0x20, 0x4000, 0x4025, 0xffffffff):
        for name_length in (0, 1, 29, 30):
            argument = bytearray(rng.randbytes(CHANNEL_ARGUMENT_SIZE))
            struct.pack_into('<I', argument, 0xc, flags)
            argument[0x10:0x30] = b'n' * name_length + bytes(32 - name_length)
            allocated = rng.randbytes(CHANNEL_ALLOCATION_SIZE)
            expected = initialize_channel_image(bytes(argument), allocated)
            oracle._reset()
            source, image = oracle.inputs, oracle.inputs + 0x1000
            cpu.mem_write(source, bytes(argument))
            cpu.mem_write(image, allocated)
            cpu.reg_write(reg.UC_X86_REG_ECX, image)
            stack = cpu.reg_read(reg.UC_X86_REG_ESP)
            cpu.mem_write(stack, struct.pack('<II', oracle.stop, source))
            oracle._run(0x743d50, oracle.stop, count=100000)
            actual = bytes(cpu.mem_read(image, CHANNEL_ALLOCATION_SIZE))
            # Native vtable identity is process-private; our boundary preserves it.
            if actual[4:] != expected[4:]:
                first = next(i for i in range(4, len(expected)) if actual[i] != expected[i])
                raise AssertionError(f'channel constructor differs at offset {first:#x}')
            # Execute original serializer-record copy range with arbitrary state.
            # These are synthetic caller/connection fields, not live values.
            arbitrary = bytearray(actual)
            for offset in (8, 0x2c, 0x30, 0x34, 0x58, 0x5c, 0x60):
                struct.pack_into('<I', arbitrary, offset, rng.getrandbits(32))
            cpu.mem_write(image, bytes(arbitrary))
            actual = bytes(arbitrary)
            expected_record = materialize_channel_record(actual).native
            cpu.reg_write(reg.UC_X86_REG_EBP, image)
            oracle._run(0x7398a7, 0x739a0e, count=10000)
            actual_record = bytes(cpu.mem_read(image + 0x1a0, 0x1a4))
            if actual_record != expected_record:
                raise AssertionError('channel record materialization differs')
            cases += 1
    return {'matched_constructor_cases': cases, 'matched_record_copy_cases': cases,
            'substituted_host_call': 'InitializeCriticalSection only; inert RET 4',
            'excluded': 'vtable identity, connection override producers, listener, sockets, live joins'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    print(json.dumps(verify(parser.parse_args().executable), indent=2))
