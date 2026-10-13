"""Compare original 0xd5 field loading, before pending lookup or network I/O."""
import argparse
import json
import struct
from client.mcots_login_response import MCOTSLoginSuccess
from tools.native_oracle import DynoOracle


def verify(executable):
    oracle = DynoOracle(executable)
    cpu, reg = oracle.cpu, oracle.reg
    globals_09 = (0xb29a50, 0xb29a54, 0xb29f84, 0xb29f78, 0xb29f60, 0xb29f80)
    globals_89 = (0xb29f64, 0xb29a58, 0xb29a5c, 0xb29a60, 0xb29a64,
                  0xb29f68, 0xb29f6c, 0xb29f70, 0xb29f74)
    for flags in (0, 5, 255):
        oracle._reset()
        payload = bytearray((index*37+flags) & 255 for index in range(173))
        struct.pack_into('<H', payload, 0, 0xd5)
        payload[6] = flags
        expected = MCOTSLoginSuccess.decode(bytes(payload))
        cpu.mem_write(oracle.inputs, bytes(payload))
        stack = cpu.reg_read(reg.UC_X86_REG_ESP)
        cpu.mem_write(stack, struct.pack('<5I', oracle.stop, 0, 0, 0, oracle.inputs))
        # Stops before the pending-transaction lookup.
        oracle._run(0x682590, 0x682679, count=1000)
        actual_09 = tuple(struct.unpack('<I', bytes(cpu.mem_read(address, 4)))[0]
                          for address in globals_09)
        actual_89 = tuple(struct.unpack('<I', bytes(cpu.mem_read(address, 4)))[0]
                          for address in globals_89)
        bits = tuple(bool(value) for value in bytes(cpu.mem_read(0xb2a0a0, 3)))
        if (actual_09, actual_89, bits) != (expected.values_09, expected.values_89, expected.native_feature_bits):
            raise ValueError('native login-success fields differ')
    return {'matched_login_field_cases': 3,
            'scope': '0xd5 scalar/feature loading only; no service connection or server acceptance'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    print(json.dumps(verify(parser.parse_args().executable), indent=2))
