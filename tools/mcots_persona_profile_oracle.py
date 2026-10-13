"""Verify the original profile supplement copy without running any services."""
import argparse
import json
import struct
from tools.native_oracle import DynoOracle


def verify(executable):
    oracle = DynoOracle(executable)
    cpu = oracle.cpu
    for seed in (0,37,255):
        oracle._reset()
        profile = bytes((index*17+seed)&255 for index in range(453))
        supplement = bytes((index*31+seed)&255 for index in range(26))
        output, source = oracle.inputs, oracle.inputs+0x1000
        cpu.mem_write(output,profile)
        cpu.mem_write(source,supplement)
        cpu.mem_write(0xb29970,struct.pack('<I',output))
        cpu.mem_write(0xb29910,struct.pack('<I',source))
        # Copy only. Stop before freeing the temporary supplement allocation.
        oracle._run(0x67be3c,0x67be59,count=1000)
        if bytes(cpu.mem_read(output,453)) != profile[:0x1ab]+supplement:
            raise ValueError('original persona profile supplement copy differs')
    return {'matched_profile_merges':3,
            'scope':'26-byte supplement copy only; no network, allocation or disposal'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    print(json.dumps(verify(parser.parse_args().executable),indent=2))
