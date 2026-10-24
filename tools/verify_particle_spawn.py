"""Compare the particle-record constructor with original 0x527060."""
import argparse
import json
import random
import struct

from client.particle_spawn import POOL_CAPACITY, RECORD_BYTES, construct_particle
from client.random_state import RandomState
from tools.native_oracle import DynoOracle

POOL = 0x00a3bfd8
FRAME = 0x00aa456c
MODE = 0x009aba34
RANDOM_WORDS = (0x8c89d0, 0x8c89d4, 0x8c89d8,
                0x8c89dc, 0x8c89e0, 0x8c89e4)


def _float_word(value):
    return struct.unpack('<I', struct.pack('<f', value))[0]


def _case(rng, index):
    config = bytearray(0x60)
    struct.pack_into('<h', config, 8, rng.randint(1, 200))
    struct.pack_into('<i', config, 0xc, rng.randint(0, 8))
    for offset in (0x10, 0x14, 0x18, 0x1c, 0x30, 0x34,
                   0x38, 0x40, 0x44, 0x48):
        struct.pack_into('<f', config, offset, rng.uniform(0.05, 3.0))
    for offset in (0x20, 0x24, 0x28, 0x4c):
        struct.pack_into('<I', config, offset, rng.getrandbits(32))
    config[0x50:0x58] = bytes(rng.randrange(256) for _ in range(8))
    config[0x5c] = rng.randrange(256)
    position = tuple(rng.randint(-100_000, 100_000) for _ in range(3))
    scale = rng.uniform(0.05, 2.0)
    vectors = tuple(tuple(rng.uniform(-10.0, 10.0) for _ in range(3))
                    for _ in range(3))
    seed = tuple(rng.getrandbits(32) for _ in range(6))
    frame = rng.randrange(0, 1000)
    mode = rng.choice((0, 0, 0, 1, 2))
    cadence_flag = rng.randrange(2)
    return (bytes(config), position, scale, vectors, seed, frame, mode,
            cadence_flag)


def _initial_pool(index):
    pool = [bytearray(RECORD_BYTES) for _ in range(POOL_CAPACITY)]
    if index % 3 == 1:
        for slot_index, slot in enumerate(pool):
            slot[:] = bytes(((slot_index + byte_index) & 0xff
                             for byte_index in range(RECORD_BYTES)))
            struct.pack_into('<h', slot, 4, 20 + slot_index % 9)
        free_index = 7 + index % (POOL_CAPACITY - 7)
        struct.pack_into('<h', pool[free_index], 4, 0)
    elif index % 3 == 2:
        for slot_index, slot in enumerate(pool):
            slot[:] = bytes(((slot_index * 3 + byte_index) & 0xff
                             for byte_index in range(RECORD_BYTES)))
            struct.pack_into('<h', slot, 4, 1 + slot_index % 11)
    return pool


def verify(executable, cases=256):
    if type(cases) is not int or not 1 <= cases <= 2048:
        raise ValueError('cases must be between 1 and 2048')
    oracle = DynoOracle(executable)
    rng = random.Random(0x527060)
    config_ptr = oracle.inputs + 0x1000
    position_ptr = oracle.inputs + 0x1100
    vector_ptrs = (oracle.inputs + 0x1120, oracle.inputs + 0x1140,
                   oracle.inputs + 0x1160)
    for index in range(cases):
        config, position, scale, vectors, seed, frame, mode, cadence_flag = _case(rng, index)
        for address, vector in zip(vector_ptrs, vectors):
            oracle.cpu.mem_write(address, struct.pack('<3f', *vector))
        oracle.cpu.mem_write(config_ptr, config)
        oracle.cpu.mem_write(position_ptr, struct.pack('<3i', *position))
        py_pool = _initial_pool(index)
        oracle.cpu.mem_write(POOL, b''.join(py_pool))
        oracle.cpu.mem_write(FRAME, struct.pack('<q', frame))
        oracle.cpu.mem_write(MODE, struct.pack('<I', mode))
        for address, word in zip(RANDOM_WORDS, seed):
            oracle.cpu.mem_write(address, struct.pack('<I', word))

        py_rng = RandomState(seed)
        py_result = construct_particle(
            config, config_ptr, position, scale, vectors[0], vectors[1],
            vectors[2], py_rng, py_pool, frame_counter=frame,
            effect_mode=mode, cadence_flag=cadence_flag)
        oracle.call(0x527060, (config_ptr, position_ptr, _float_word(scale),
                              *vector_ptrs, cadence_flag),
                    instruction_limit=1_000_000)
        native_pointer = oracle.cpu.reg_read(oracle.reg.UC_X86_REG_EAX)
        native_result = None if native_pointer == 0 else (native_pointer - POOL) // RECORD_BYTES
        native_pool = bytes(oracle.cpu.mem_read(POOL, POOL_CAPACITY * RECORD_BYTES))
        native_rng = tuple(struct.unpack('<I', oracle.cpu.mem_read(address, 4))[0]
                           for address in RANDOM_WORDS)
        expected_pool = b''.join(py_pool)
        if (native_result != py_result or native_pool != expected_pool or
                native_rng != py_rng.words):
            raise AssertionError(
                f'case {index}: ptr slot native={native_result}, model={py_result}; '
                f'pool_equal={native_pool == expected_pool}; '
                f'rng_native={native_rng!r}; rng_model={py_rng.words!r}')
    return {'entry': '0x527060', 'cases': cases,
            'scope': 'full 600-slot pool image, free-slot and minimum-lifetime '
                     'selection, supplied emitter/input/global state, gating, '
                     'record bytes and RNG transition'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    parser.add_argument('--cases', type=int, default=256)
    args = parser.parse_args()
    print(json.dumps(verify(args.executable, args.cases)))


if __name__ == '__main__':
    main()
