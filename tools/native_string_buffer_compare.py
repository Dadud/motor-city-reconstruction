"""Compare native and Python unique-inline string buffer assignment."""
import json
import random
import subprocess

from client.string_buffer import assign_inline_buffer


def verify(runner, cases=512):
    rng = random.Random(0x415410)
    rows = []
    for index in range(cases):
        capacity = rng.randrange(1, 32)
        length = rng.randrange(1, capacity + 1)
        source_offset = 4 if index % 2 == 0 else 40
        destination_offset = 40 if index % 2 == 0 else 4
        memory = bytearray(rng.randrange(256) for _ in range(80))
        source = bytes(memory[source_offset:source_offset + 33])
        expected = bytearray(memory)
        assign_inline_buffer(memoryview(expected)[destination_offset:destination_offset + 33],
                             source, length, capacity)
        fields = [length, capacity, *memory, source_offset, destination_offset]
        rows.append(('0 ' + ' '.join(map(str, fields)), expected, length))
    result = subprocess.run([str(runner)], input='\n'.join(row for row, _, _ in rows) + '\n',
                            capture_output=True, text=True, check=True, timeout=30)
    output = result.stdout.splitlines()
    if len(output) != cases:
        raise AssertionError(('row count', len(output), cases))
    for index, (line, (_, expected, length)) in enumerate(zip(output, rows)):
        values = list(map(int, line.split()))
        if len(values) != 81 or bytes(values[1:]) != expected:
            raise AssertionError(('native bytes', index, values[:4]))
        if values[0] != length:
            raise AssertionError(('native length', index, values[0]))
    return {'cases': cases, 'bytes': 'exact',
            'scope': '0x415410 unique inline buffer, nonzero length, capacity below 32; allocation and shared-buffer paths excluded'}
if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('runner'); parser.add_argument('--cases', type=int, default=512)
    args = parser.parse_args(); print(json.dumps(verify(args.runner, args.cases)))
