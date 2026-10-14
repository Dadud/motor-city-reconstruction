"""Bounded original settings transfer, with separate synthetic source/destination.

Executes 0x44db80 and 0x44a9d0 without substituted calls, imports or startup.
Only safe, terminated strings are covered; aliases and overflows are excluded.
"""
import argparse
import itertools
import json
import random
import struct

from client.room_settings import apply_room_settings, ROOM_SETTINGS_MIN_SIZE
from tools.native_oracle import DynoOracle


def verify(executable):
    oracle = DynoOracle(executable)
    cpu, reg = oracle.cpu, oracle.reg
    destination, source = oracle.inputs, oracle.inputs + 0x1000
    rng = random.Random(0x44db80)
    count = 0
    for name_size, secondary_size, _ in itertools.product((0, 1, 29, 30, 31), (0, 1, 14, 15), range(4)):
        oracle._reset()
        room = rng.randbytes(0x3c0)
        settings = bytearray(rng.randbytes(ROOM_SETTINGS_MIN_SIZE + 17))
        settings[:name_size+1] = b'n'*name_size + b'\0'
        settings[0x30:0x30+secondary_size+1] = b's'*secondary_size + b'\0'
        cpu.mem_write(destination, room)
        cpu.mem_write(source, bytes(settings))
        cpu.reg_write(reg.UC_X86_REG_ECX, destination)
        stack = cpu.reg_read(reg.UC_X86_REG_ESP)
        cpu.mem_write(stack, struct.pack('<II', oracle.stop, source))
        oracle._run(0x44db80, oracle.stop, count=10000)
        if bytes(cpu.mem_read(destination, len(room))) != apply_room_settings(room, bytes(settings)):
            raise AssertionError('original settings assignment differs')
        if cpu.reg_read(reg.UC_X86_REG_EAX) != destination:
            raise AssertionError('original settings transfer receiver return differs')
        if bytes(cpu.mem_read(source, len(settings))) != bytes(settings):
            raise AssertionError('original settings transfer changed source')
        count += 1
    return {'matched_settings_transfers': count, 'substituted_boundaries': [],
            'coverage': 'original44db80 and44a9d0 entry through return',
            'aliasing_and_overflow_tested': False, 'live_server_tested': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    print(json.dumps(verify(parser.parse_args().executable), indent=2))
