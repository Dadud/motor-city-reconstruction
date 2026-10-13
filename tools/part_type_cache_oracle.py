"""Verify bounded original post-load type-cache reference resolution."""
import argparse
import json
import random
import struct
from client.part_type_templates import resolve_part_type_cache
from tools.native_oracle import DynoOracle


def synthetic_cases():
    rng = random.Random(0x64d1e9)
    for case in range(64):
        marker = bytearray(1596)
        text = b'==No Parent Marker==\0'
        marker[0x347:0x347 + len(text)] = text
        records = [bytes(marker)]
        for _ in range(case % 16):
            record = bytearray(b'\x35' * 1596)
            struct.pack_into('<3i', record, 0, rng.choice((1, 2, 3, -4)),
                             rng.choice((0, 1, 2, -4, 99)), rng.choice((0, 1, 3, -4, 99)))
            struct.pack_into('<ii', record, 0x600, rng.choice((-1, 0, 7)), rng.choice((-1, 0, 8)))
            records.append(bytes(record))
        yield tuple(records)


def verify(executable):
    oracle = DynoOracle(executable)
    cpu = oracle.cpu
    matched = 0
    for case, records in enumerate(synthetic_cases()):
        oracle._reset()
        cpu.mem_write(oracle.inputs, b''.join(records))
        cpu.mem_write(0xb18018, struct.pack('<II', len(records), oracle.inputs))
        oracle._run(0x64d1e9, 0x64d297, count=100000)
        expected = resolve_part_type_cache(records)
        if bytes(cpu.mem_read(oracle.inputs, len(records) * 1596)) != b''.join(expected):
            raise ValueError(f'original type-cache resolution differs in case {case}')
        matched += 1
    return {'matched_cache_resolution_cases': matched,
            'scope': 'original 0x64d1e9..0x64d297 reference resolution; supplied cache records; allocation/SQL/row encoding excluded'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    print(json.dumps(verify(parser.parse_args().executable), indent=2))
