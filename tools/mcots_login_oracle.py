"""Compare the native MCOTS login record builder; no network calls execute."""
import argparse
import json
import struct
from client.mcots_login import MCOTSLoginRecord
from tools.native_oracle import DynoOracle


def verify(executable):
    oracle = DynoOracle(executable)
    cpu, reg = oracle.cpu, oracle.reg
    for name in (b'', b'persona', b'n'*13, b'n'*32):
        expected = MCOTSLoginRecord(0x12345678, 42, name, 11, 22, 33)
        oracle._reset()
        output, task, source = oracle.inputs, oracle.inputs+0x1000, oracle.inputs+0x2000
        cpu.mem_write(output, b'\xa5'*39)
        cpu.mem_write(task, bytes(300))
        cpu.mem_write(task+0x120, struct.pack('<3I', 11, 22, 33))
        cpu.mem_write(source, name+b'\0')
        cpu.mem_write(oracle.frame+8, struct.pack('<3I', expected.account_user_id,
                                                expected.persona_id, source))
        cpu.mem_write(oracle.frame+0x20, struct.pack('<I', task))
        cpu.reg_write(reg.UC_X86_REG_EDX, output)
        # Includes the real native strncpy, stops before transaction queueing.
        oracle._run(0x683028, 0x68307b, count=10000)
        if bytes(cpu.mem_read(output, 39)) != expected.encode_native_record():
            raise ValueError('native MCOTS login record differs')
    return {'matched_native_record_cases': 4,
            'scope': '39-byte record construction only; no attachment, wire codec or server test'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    print(json.dumps(verify(parser.parse_args().executable), indent=2))
