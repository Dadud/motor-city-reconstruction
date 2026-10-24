"""Compare trail-record aging and counts with original routine 0x527360."""
import argparse
import json
import random
import struct

from client.particle_update import (TRAIL_CAPACITY, TRAIL_RECORD_BYTES,
                                    advance_particle_trails)
from tools.native_oracle import DynoOracle

POOL = 0x00a4be20
TYPE_COUNTS = 0x00a4bcf8


def verify(executable, cases=128):
    if type(cases) is not int or not 1 <= cases <= 2048:
        raise ValueError('cases must be between 1 and 2048')
    oracle = DynoOracle(executable)
    rng = random.Random(0x527360)
    for case in range(cases):
        records = []
        definitions = {}
        definition_tokens = tuple(oracle.inputs + 0x3000 + i * 0x100
                                  for i in range(16))
        for token in definition_tokens:
            definition = bytearray(0x84)
            effect_type = rng.choice((-1, 0, 1, 2, 25, 26, rng.randrange(1, 40)))
            duration = rng.randint(1, 500)
            weight = rng.randrange(256)
            struct.pack_into('<i', definition, 0, effect_type)
            struct.pack_into('<i', definition, 0x70, duration)
            definition[0x83] = weight
            definitions[token] = bytes(definition)
            oracle.cpu.mem_write(token, bytes(definition))

        for _ in range(TRAIL_CAPACITY):
            record = bytearray(rng.getrandbits(8) for _ in range(TRAIL_RECORD_BYTES))
            token = rng.choice(definition_tokens)
            count = rng.choice((0, 0, rng.randint(-100_000, 100_000)))
            struct.pack_into('<Ii', record, 0, token, count)
            records.append(record)
        type_counts = [rng.randint(0, 100_000) for _ in range(26)]
        oracle.cpu.mem_write(POOL, b''.join(records))
        oracle.cpu.mem_write(TYPE_COUNTS, struct.pack('<26I', *type_counts))

        advance_particle_trails(records, definitions, type_counts)
        oracle.call(0x527360, (0,), instruction_limit=2_000_000)
        native_pool = bytes(oracle.cpu.mem_read(POOL, TRAIL_CAPACITY * TRAIL_RECORD_BYTES))
        native_counts = struct.unpack('<26I', oracle.cpu.mem_read(TYPE_COUNTS, 26 * 4))
        if native_pool != b''.join(records) or native_counts != tuple(v & 0xffffffff for v in type_counts):
            mismatch = next((offset for offset, (a, b) in enumerate(
                zip(native_pool, b''.join(records))) if a != b), None)
            raise AssertionError(
                f'case {case}: trail pool differs at {mismatch}; '
                f'counts_equal={native_counts == tuple(v & 0xffffffff for v in type_counts)}')
    return {'entry': '0x527360', 'cases': cases,
            'scope': 'all 200 records and 26 type counters, supplied definitions, '
                     'count aging and progress-byte termination'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    parser.add_argument('--cases', type=int, default=128)
    args = parser.parse_args()
    print(json.dumps(verify(args.executable, args.cases)))


if __name__ == '__main__':
    main()
