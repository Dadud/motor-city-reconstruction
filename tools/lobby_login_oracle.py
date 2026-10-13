"""Compare connection login payload with bounded original x86 execution."""
import argparse
import json
import struct

from client.lobby_login import LobbyLogin
from tools.native_oracle import DynoOracle


def verify(executable):
    oracle = DynoOracle(executable)
    cpu, reg = oracle.cpu, oracle.reg
    cases = [LobbyLogin(42, b'driver', bytes(range(64)), 7, 9, b'4.5.0.0',
                        b'host', b'127.0.0.1', bytes(range(16))),
             LobbyLogin(0xffffffff, b'', bytes(64), 0, 0xffffffff,
                        b'', b'', b'', bytes(16)),
             LobbyLogin(1, b'n'*31, b'k'*64, 0xffffffff, 2,
                        b'v'*31, b'h'*63, b'1'*15, b'x'*16)]
    for case in cases:
        oracle._reset()
        source, output = oracle.inputs, oracle.inputs+0x1000
        cpu.mem_write(source, bytes(256))
        for offset, value in ((0, case.user_id), (100, case.value_100), (200, case.value_200)):
            cpu.mem_write(source+offset, struct.pack('<I', value))
        for offset, value in ((4, case.username), (0x24, case.key_blob),
                              (0x68, case.opaque_16), (0x78, case.hostname),
                              (0xb8, case.ip_address), (0xcc, case.version)):
            cpu.mem_write(source+offset, value or b'\0')
        cpu.reg_write(reg.UC_X86_REG_ECX, oracle.inputs+0x2000)
        stack = cpu.reg_read(reg.UC_X86_REG_ESP)
        cpu.mem_write(stack, struct.pack('<IIII', oracle.stop, output, 255, source))
        oracle._run(0x7e47d0, oracle.stop, count=100000)
        length = cpu.reg_read(reg.UC_X86_REG_EAX)
        expected = case.payload()
        if length != len(expected) or bytes(cpu.mem_read(output, length)) != expected:
            raise ValueError('connection login differs from original packing')
    return {'matched_cases': len(cases), 'coverage': 'native payload packer; no connection or server test'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    print(json.dumps(verify(parser.parse_args().executable), indent=2))
