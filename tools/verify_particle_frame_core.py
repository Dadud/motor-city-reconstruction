"""Compare the supported direct-update slice of original 0x527490."""
import argparse
import json
import random
import struct

from client.particle_spawn import POOL_CAPACITY, RECORD_BYTES
from client.particle_update import (TRAIL_CAPACITY, TRAIL_RECORD_BYTES,
                                    advance_particle_frame_core)
from tools.native_oracle import DynoOracle

PARTICLES = 0x00a3bfd8
TYPE_COUNTS = 0x00a4bcf8
TRAILS = 0x00a4be20
FRAME = 0x00aa456c


def _f32(value):
    return struct.unpack('<f', struct.pack('<f', value))[0]


def verify(executable, cases=128):
    if type(cases) is not int or not 1 <= cases <= 1024:
        raise ValueError('cases must be between 1 and 1024')
    oracle = DynoOracle(executable)
    rng = random.Random(0x527490)
    for case in range(cases):
        frame = rng.randrange(0, 10_000) & ~1
        if case % 2:
            frame |= 2
        sources = {}
        tokens = tuple(oracle.inputs + 0x4000 + i * 0x100 for i in range(16))
        for token in tokens:
            source = bytearray(0x84)
            struct.pack_into('<i', source, 0, rng.choice((-1, 0, 1, 3, 25, 26)))
            struct.pack_into('<f', source, 0x38, _f32(rng.uniform(0.1, 1.5)))
            # Keep child-emitter, direction and fade branches disabled.
            struct.pack_into('<I', source, 0x3c, 0)
            struct.pack_into('<I', source, 0x50, 0)
            struct.pack_into('<I', source, 0x68, 0)
            struct.pack_into('<i', source, 0x70, rng.randint(1, 500))
            source[0x83] = rng.randrange(256)
            sources[token] = bytes(source)
            oracle.cpu.mem_write(token, bytes(source))

        particles = []
        for _ in range(POOL_CAPACITY):
            slot = bytearray(rng.getrandbits(8) for _ in range(RECORD_BYTES))
            active = rng.randrange(4) != 0
            token = rng.choice(tokens) if active and rng.randrange(5) else 0
            struct.pack_into('<Ih', slot, 0, token, rng.randint(1, 5) if active else 0)
            for offset in (0xc, 0x10, 0x14, 0x18, 0x1c, 0x20,
                           0x24, 0x2c, 0x30, 0x34):
                struct.pack_into('<f', slot, offset, _f32(rng.uniform(-20., 20.)))
            struct.pack_into('<f', slot, 0x3c, 0.)
            slot[0x68] = 0
            particles.append(slot)

        trails = []
        for _ in range(TRAIL_CAPACITY):
            record = bytearray(rng.getrandbits(8) for _ in range(TRAIL_RECORD_BYTES))
            struct.pack_into('<Ii', record, 0, rng.choice(tokens), rng.choice((0, 0, rng.randint(1, 50))))
            trails.append(record)
        counters = [rng.getrandbits(32) for _ in range(52)]
        oracle.cpu.mem_write(PARTICLES, b''.join(particles))
        oracle.cpu.mem_write(TRAILS, b''.join(trails))
        oracle.cpu.mem_write(TYPE_COUNTS, struct.pack('<52I', *counters))
        oracle.cpu.mem_write(FRAME, struct.pack('<i', frame))

        advance_particle_frame_core(particles, sources, trails, counters, frame)
        oracle.call(0x527490, instruction_limit=2_000_000)
        native_particles = bytes(oracle.cpu.mem_read(PARTICLES, POOL_CAPACITY * RECORD_BYTES))
        native_trails = bytes(oracle.cpu.mem_read(TRAILS, TRAIL_CAPACITY * TRAIL_RECORD_BYTES))
        native_counters = struct.unpack('<52I', oracle.cpu.mem_read(TYPE_COUNTS, 52 * 4))
        if (native_particles != b''.join(particles) or
                native_trails != b''.join(trails) or
                native_counters != tuple(value & 0xffffffff for value in counters)):
            raise AssertionError(f'case {case}: parent update state differed')
    return {'entry': '0x527490', 'cases': cases,
            'scope': 'supported direct update slice, all 600 particle slots, '
                     '200 trails and 52 counters; child-emitter/spin/fade/respawn disabled'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    parser.add_argument('--cases', type=int, default=128)
    args = parser.parse_args()
    print(json.dumps(verify(args.executable, args.cases)))


if __name__ == '__main__':
    main()
