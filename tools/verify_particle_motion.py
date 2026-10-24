"""Compare particle motion integration with original routine 0x5273f0."""
import argparse
import json
import random
import struct

from client.particle_spawn import POOL_CAPACITY, RECORD_BYTES
from client.particle_update import advance_particle_motion
from tools.native_oracle import DynoOracle

POOL = 0x00a3bfd8
FRAME = 0x00aa456c
LAST_UPDATE = 0x00a51be0


def _f32(value):
    return struct.unpack('<f', struct.pack('<f', value))[0]


def _build_case(rng, oracle, case):
    source_count = 12
    source_tokens = tuple(oracle.inputs + 0x2000 + i * 0x80
                          for i in range(source_count))
    acceleration = {}
    for token in source_tokens:
        value = _f32(rng.uniform(-20.0, 20.0))
        acceleration[token] = value
        source = bytearray(0x40)
        struct.pack_into('<f', source, 0x2c, value)
        oracle.cpu.mem_write(token, bytes(source))

    pool = []
    for _ in range(POOL_CAPACITY):
        slot = bytearray(rng.getrandbits(8) for _ in range(RECORD_BYTES))
        active = rng.randrange(0, 4) != 0
        token = rng.choice(source_tokens) if rng.randrange(0, 5) else 0
        struct.pack_into('<Ih', slot, 0, token, rng.randint(1, 120) if active else 0)
        for offset in (0xc, 0x10, 0x14, 0x18, 0x1c, 0x20,
                       0x24, 0x2c, 0x30, 0x34):
            struct.pack_into('<f', slot, offset, _f32(rng.uniform(-100.0, 100.0)))
        pool.append(slot)

    current = rng.randint(0, 3000)
    if case % 5 == 0:
        last = current >> 1
    elif case % 5 == 1:
        last = (current >> 1) + 1
    else:
        last = rng.randint(0, 1000)
    return pool, acceleration, current, last


def verify(executable, cases=128):
    if type(cases) is not int or not 1 <= cases <= 2048:
        raise ValueError('cases must be between 1 and 2048')
    oracle = DynoOracle(executable)
    rng = random.Random(0x5273F0)
    for index in range(cases):
        pool, acceleration, current, last = _build_case(rng, oracle, index)
        oracle.cpu.mem_write(POOL, b''.join(pool))
        oracle.cpu.mem_write(FRAME, struct.pack('<i', current))
        oracle.cpu.mem_write(LAST_UPDATE, struct.pack('<i', last))

        expected_last = advance_particle_motion(pool, acceleration, current, last)
        oracle.call(0x5273F0, instruction_limit=2_000_000)
        actual_pool = bytes(oracle.cpu.mem_read(POOL, POOL_CAPACITY * RECORD_BYTES))
        expected_pool = b''.join(pool)
        actual_last = struct.unpack('<i', oracle.cpu.mem_read(LAST_UPDATE, 4))[0]
        if actual_pool != expected_pool or actual_last != expected_last:
            mismatch = next((offset for offset, (a, b) in enumerate(
                zip(actual_pool, expected_pool)) if a != b), None)
            raise AssertionError(
                f'case {index}: pool differs at {mismatch!r}; '
                f'last tick native={actual_last}, expected={expected_last}; '
                f'current={current}, initial last={last}')
    return {'entry': '0x5273f0', 'cases': cases,
            'scope': 'full 600-slot pool, supplied source Y acceleration, '
                     'positive/zero/negative tick delta, exact record bytes'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    parser.add_argument('--cases', type=int, default=128)
    args = parser.parse_args()
    print(json.dumps(verify(args.executable, args.cases)))


if __name__ == '__main__':
    main()
