"""Compare original attachment payload construction without sending it."""
import argparse
import json
import struct
from client.mcots_attachment import MCOTSAttachment
from tools.native_oracle import DynoOracle


def verify(executable):
    oracle = DynoOracle(executable)
    cpu, reg = oracle.cpu, oracle.reg
    for name in (b'', b'persona', b'n'*12, b'n'*13, b'n'*32):
        oracle._reset()
        output, source = oracle.inputs, oracle.inputs+0x1000
        expected = MCOTSAttachment(0x12345678, 42, name)
        cpu.mem_write(output, b'\xa5'*40)
        cpu.mem_write(source, name+b'\0')
        cpu.mem_write(oracle.frame+0xc, struct.pack('<3I', expected.account_user_id,
                                                expected.persona_id, source))
        cpu.reg_write(reg.UC_X86_REG_EBX, output)
        # Includes original strncpy and explicit final NUL. Stops immediately
        # before the task allocation call; no allocation or socket I/O executes.
        oracle._run(0x68230d, 0x682348, count=10000)
        if bytes(cpu.mem_read(output, 40)) != expected.encode():
            raise ValueError('native MCOTS attachment payload differs')
    return {'matched_attachment_payloads': 5,
            'scope': '40-byte attachment construction only; no task allocation or network I/O'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    print(json.dumps(verify(parser.parse_args().executable), indent=2))
