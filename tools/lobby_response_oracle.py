"""Replay native lp b success-field reader with synthetic payloads only."""
import argparse
import json
import struct
from client.lobby_response import LobbyLoginSuccess
from client.nps_framing import Frame
from tools.native_oracle import DynoOracle


def verify(executable):
    oracle = DynoOracle(executable)
    cpu, reg = oracle.cpu, oracle.reg
    checked = 0
    for message_id in (0x120, 0x308):
        for name in (b'', b'driver\0', b'a\0b', b'n'*31, b'n'*32):
            oracle._reset()
            source, output = oracle.inputs, oracle.inputs+0x1000
            blob = bytes(range(64))
            payload = struct.pack('>II', 0xfedcba98, len(name))+name+blob
            expected = LobbyLoginSuccess.from_frame(Frame(message_id, payload))
            cpu.mem_write(source, payload)
            cpu.mem_write(output, bytes(128))
            stack = cpu.reg_read(reg.UC_X86_REG_ESP)
            # cdecl varargs: object, input, length, format, uint32*, string*,
            # string capacity, fixed-byte destination, fixed-byte count.
            cpu.mem_write(stack, struct.pack('<10I', oracle.stop, 0, source,
                len(payload), 0x8e0660, output, output+4, 32, output+36, 64))
            oracle._run(0x7e42e0, oracle.stop, count=100000)
            if cpu.reg_read(reg.UC_X86_REG_EAX) != len(payload):
                raise ValueError('native reader consumed a different length')
            if struct.unpack('<I', cpu.mem_read(output, 4))[0] != expected.user_id:
                raise ValueError('native user ID differs')
            native_name = bytes(cpu.mem_read(output+4, 32)).split(b'\0', 1)[0]
            if native_name != expected.native_username:
                raise ValueError('native bounded username differs')
            if bytes(cpu.mem_read(output+36, 64)) != expected.caller_blob:
                raise ValueError('native fixed blob differs')
            checked += 1
    return {'matched_cases': checked, 'coverage': 'native field reader; opcode branches traced statically; no server test'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    print(json.dumps(verify(parser.parse_args().executable), indent=2))
