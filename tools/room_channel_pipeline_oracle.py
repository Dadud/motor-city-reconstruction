"""Compare room-produced arguments through original channel data/serialization.

Uses explicit synthetic allocation and caller/connection fields, without sockets
or authenticated state. Producer correctness has its separate original oracle.
"""
import argparse
import json
import random
import struct

from client.lobby_channel_record import initialize_channel_image, materialize_channel_record
from client.room_join_request import RoomJoinInputs, build_room_join_argument
from tools.native_oracle import DynoOracle


def verify(executable):
    oracle = DynoOracle(executable)
    cpu, reg = oracle.cpu, oracle.reg
    lock_stub = oracle.stub + 0xe000
    cpu.mem_write(lock_stub, b'\xc2\x04\x00')
    cpu.mem_write(0x83b27c, struct.pack('<I', lock_stub))
    rng = random.Random(0x44cf80)
    cases = 0
    for name_length in (0, 1, 29, 30, 31):
        for password in (None, b'p', b'p' * 16):
            for flag in (False, True):
                inputs = RoomJoinInputs(rng.getrandbits(32), 0x21, rng.getrandbits(32),
                                        b'n' * name_length, 16, rng.randbytes(256))
                argument = build_room_join_argument(inputs, password=password, flag_0x20=flag)
                # Supplied zero allocation is a controlled input, not a claim
                # about the original allocator or original online startup.
                allocated = bytes(0x3bc)
                expected_image = bytearray(initialize_channel_image(argument, allocated))
                oracle._reset()
                source, image = oracle.inputs, oracle.inputs + 0x1000
                cpu.mem_write(source, argument)
                cpu.mem_write(image, allocated)
                cpu.reg_write(reg.UC_X86_REG_ECX, image)
                stack = cpu.reg_read(reg.UC_X86_REG_ESP)
                cpu.mem_write(stack, struct.pack('<II', oracle.stop, source))
                oracle._run(0x743d50, oracle.stop, count=100000)
                if bytes(cpu.mem_read(image + 4, 0x3b8)) != bytes(expected_image[4:]):
                    raise AssertionError('room/channel constructor pipeline differs')
                for offset in (8, 0x2c, 0x30, 0x34, 0x58, 0x5c, 0x60):
                    value = rng.getrandbits(32)
                    struct.pack_into('<I', expected_image, offset, value)
                    cpu.mem_write(image + offset, struct.pack('<I', value))
                expected_record = materialize_channel_record(bytes(expected_image))
                cpu.reg_write(reg.UC_X86_REG_EBP, image)
                oracle._run(0x7398a7, 0x739a0e, count=10000)
                if bytes(cpu.mem_read(image + 0x1a0, 0x1a4)) != expected_record.native:
                    raise AssertionError('room/channel record pipeline differs')
                expected_payload = expected_record.payload()
                oracle._reset()
                output, context = oracle.inputs + 0x3000, oracle.inputs + 0x4000
                cpu.mem_write(output, bytes(0x400))
                cpu.mem_write(context, bytes(16))
                cpu.reg_write(reg.UC_X86_REG_ECX, context)
                stack = cpu.reg_read(reg.UC_X86_REG_ESP)
                cpu.mem_write(stack, struct.pack('<IIII', oracle.stop, output, 0x170, image + 0x1a0))
                oracle._run(0x7e4c30, oracle.stop, count=100000)
                size = cpu.reg_read(reg.UC_X86_REG_EAX)
                if size != len(expected_payload) or bytes(cpu.mem_read(output, size)) != expected_payload:
                    raise AssertionError('room/channel payload pipeline differs')
                cases += 1
    return {'matched_room_channel_pipeline_cases': cases,
            'substituted_boundary': 'InitializeCriticalSection only; inert RET 4',
            'supplied_allocation': 'explicit zero image',
            'excluded': 'original producer execution, caller/connection field origins, transport, live joining',
            'live_server_tested': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    print(json.dumps(verify(parser.parse_args().executable), indent=2))
