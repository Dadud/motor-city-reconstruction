"""Compare the 0x6f1160 vector-dot batch with original execution."""
import argparse
import json
import random
import struct

from client.matrix_math import dot_product_batch
from tools.native_oracle import DynoOracle


VECTORS, DIRECTION, OUTPUT = 0x71001000, 0x71004000, 0x71004020


def verify(executable, cases=512):
    if type(cases) is not int or not 1 <= cases <= 10_000:
        raise ValueError('cases must be between 1 and 10000')
    oracle = DynoOracle(executable)
    rng = random.Random(0x6F1160)
    for case in range(cases):
        count = case % 17
        vectors = tuple(tuple(rng.uniform(-1e4, 1e4) for _ in range(3))
                        for _ in range(count))
        direction = tuple(rng.uniform(-1e4, 1e4) for _ in range(3))
        expected = dot_product_batch(vectors, direction)
        vector_data = b''.join(struct.pack('<3f', *vector) for vector in vectors)
        oracle._reset()
        if vector_data:
            oracle.cpu.mem_write(VECTORS, vector_data)
        oracle.cpu.mem_write(DIRECTION, struct.pack('<3f', *direction))
        oracle.cpu.mem_write(OUTPUT, b'\xa5' * (count * 4 + 4))
        oracle.call(0x6F1160, (count, VECTORS, DIRECTION, OUTPUT),
                    instruction_limit=100_000)
        actual_words = struct.unpack('<' + 'I' * count,
                                     oracle.cpu.mem_read(OUTPUT, count * 4)) if count else ()
        expected_words = tuple(struct.unpack('<I', struct.pack('<f', value))[0]
                               for value in expected)
        if actual_words != expected_words:
            actual = tuple(struct.unpack('<f', struct.pack('<I', word))[0]
                           for word in actual_words)
            raise AssertionError(
                f'case {case}: native={actual!r}, expected={expected!r}, '
                f'count={count}, direction={direction!r}')
        untouched = bytes(oracle.cpu.mem_read(OUTPUT + count * 4, 4))
        if untouched != b'\xa5' * 4:
            raise AssertionError(f'case {case}: batch wrote beyond count={count}: {untouched.hex()}')
    return {'entry': '0x6f1160', 'cases': cases,
            'scope': 'consecutive three-vector dot products, including zero count and untouched output tail'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    parser.add_argument('--cases', type=int, default=512)
    args = parser.parse_args()
    print(json.dumps(verify(args.executable, args.cases)))


if __name__ == '__main__':
    main()
