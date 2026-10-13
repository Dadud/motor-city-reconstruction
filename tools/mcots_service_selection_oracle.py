"""Check the installed client's service-selection writes without network I/O."""
import argparse
import json
import struct
from tools.native_oracle import DynoOracle


def verify(executable):
    oracle = DynoOracle(executable)
    cpu, reg = oracle.cpu, oracle.reg
    # (advertised IDs, configured IDs, open handles, expected index writes).
    cases = (
        ((255,)*4, (254,255,255,255), (1,0,0,0), ()),
        ((1,2,3,4), (254,255,255,255), (1,0,0,0), (1,)),
        ((7,255,255,255), (254,255,7,255), (1,0,0,0), (2,)),
        ((7,7,255,255), (254,255,7,255), (1,0,2,0), ()),
        ((1,2,3,4), (254,8,9,10), (1,2,3,4), ()),
    )
    for ids, configured, handles, changed in cases:
        oracle._reset()
        slots = bytearray(4*0x138)
        for index, (service, handle) in enumerate(zip(configured, handles)):
            struct.pack_into('<II', slots, index*0x138, handle, 99)
            struct.pack_into('<I', slots, index*0x138+0x11c, service)
        expected = bytearray(slots)
        for index in changed:
            struct.pack_into('<I', expected, index*0x138+4, index)
        payload = bytearray(173)
        for index, service in enumerate(ids):
            offset = 0x21+index*26
            struct.pack_into('<I', payload, offset, service)
            # Nonzero distinct bytes would reveal any descriptor copy.
            payload[offset+4:offset+26] = bytes([0x80+index])*22
        cpu.mem_write(0xb29a80, bytes(slots))
        cpu.mem_write(oracle.inputs, bytes(payload))
        cpu.reg_write(reg.UC_X86_REG_EBX, oracle.inputs)
        # Includes selection for all four advertised records. Stop before the
        # subsequent connection walk; no calls or host services execute.
        oracle._run(0x682824, 0x6828cd, count=5000)
        if bytes(cpu.mem_read(0xb29a80, len(slots))) != bytes(expected):
            raise ValueError('native service-selection writes differ')
    return {'matched_service_selection_cases': len(cases),
            'scope': 'original selection loop only; descriptors unchanged; no network I/O'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    print(json.dumps(verify(parser.parse_args().executable), indent=2))
