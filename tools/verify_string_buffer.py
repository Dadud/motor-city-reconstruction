"""Compare original 0x415410 unique-inline buffer assignment with Python."""
import json
import random
import struct

from client.string_buffer import assign_inline_buffer
from tools.native_oracle import DynoOracle


def verify(executable, cases=512):
    oracle = DynoOracle(executable)
    cpu = oracle.cpu
    rng = random.Random(0x415410)
    owner, destination, source = oracle.inputs + 0x100, oracle.inputs + 0x1000, oracle.inputs + 0x2000
    for index in range(cases):
        capacity = rng.randrange(1, 32)
        length = rng.randrange(1, capacity + 1)
        old_length = rng.randrange(capacity + 1)
        refcount = (0, 0xff)[index & 1]
        initial = bytes(rng.randrange(256) for _ in range(33))
        source_bytes = bytes(rng.randrange(256) for _ in range(33))
        cpu.mem_write(destination - 1, bytes((refcount,)) + initial)
        cpu.mem_write(source, source_bytes)
        cpu.mem_write(owner, struct.pack('<4I', 0, destination, old_length, capacity))
        oracle.call(0x415410, (source, length), this_pointer=owner,
                    cleanup=b'', instruction_limit=5000)
        expected = bytearray(initial)
        assign_inline_buffer(expected, source_bytes, length, capacity)
        actual = bytes(cpu.mem_read(destination, 33))
        actual_length = struct.unpack('<I', cpu.mem_read(owner + 8, 4))[0]
        if actual != bytes(expected) or actual_length != length:
            offset = next((i for i, (a, b) in enumerate(zip(actual, expected)) if a != b), None)
            raise AssertionError((index, capacity, length, refcount, actual_length, offset,
                                  actual[offset:offset+8].hex() if offset is not None else '',
                                  bytes(expected[offset:offset+8]).hex() if offset is not None else ''))
    return {'cases': cases, 'result': 'exact',
            'scope': 'original 0x415410 with unique inline destination, nonzero fitting lengths, and both native unique-buffer header sentinels; allocation and shared-buffer paths excluded'}


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable'); parser.add_argument('--cases', type=int, default=512)
    args = parser.parse_args(); print(json.dumps(verify(args.executable, args.cases)))
