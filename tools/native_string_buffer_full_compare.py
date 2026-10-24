"""Compare the bounded complete mapped 0x415410 paths across Python and C++."""
import json
import random
import subprocess

from client.string_buffer import BufferRecord, assign_buffer


def cases(count=512):
    rng = random.Random(0x415410b)
    for index in range(count):
        capacity = rng.choice((0, 1, 7, 30, 31, 32, 40, 63))
        old_length = rng.randrange(capacity + 1)
        header = rng.choice((0, 0xff, 1, 2, 7))
        if index % 5 == 0:
            header = 256  # null data pointer
            capacity = old_length = 0
        length = rng.randrange(0, 65)
        source_offset = 80
        image = bytearray(rng.randrange(256) for _ in range(160))
        if header != 256:
            image[0] = header
        yield length, capacity, old_length, header, source_offset, image


def run(binary, count=512):
    lines = []
    expected = []
    for length, capacity, old_length, header, source_offset, image in cases(count):
        if length > 64:
            raise AssertionError('case exceeds fixed source image')
        # Keep a live view over the original image so its bytes and shared
        # reference header are reflected in the emitted comparison image.
        old_storage = None if header == 256 else memoryview(image)[:capacity + 2]
        record = BufferRecord(old_storage, old_length, capacity)
        allocations, releases = [], []

        def allocate(size):
            allocations.append(size)
            return bytearray(size)

        source = memoryview(image)[source_offset:source_offset + length]
        try:
            result = assign_buffer(record, source, length, allocate, releases.append)
        except Exception as error:
            raise AssertionError((length, capacity, old_length, header, error)) from error
        fresh = record.storage if record.storage is not None and record.storage is not old_storage else None
        output = bytearray(128)
        if fresh is not None:
            output[:len(fresh)] = fresh
        # Materialize mutable views for JSON transport after the model changes.
        expected.append([result, record.length, record.capacity, len(releases),
                         allocations[0] if allocations else 0, *image, *output])
        lines.append('0 ' + ' '.join(map(str, (length, capacity, old_length,
                     header, source_offset, *image))))

    process = subprocess.run([str(binary)], input='\n'.join(lines) + '\n', text=True,
                             capture_output=True, check=True)
    actual = [[int(value) for value in line.split()] for line in process.stdout.splitlines()]
    if actual != expected:
        first = next(i for i, (a, b) in enumerate(zip(actual, expected)) if a != b)
        raise AssertionError({'case': first, 'native': actual[first][:10],
                              'python': expected[first][:10]})
    return {'cases': count, 'result': 'exact',
            'scope': 'mapped 0x415410 inline, empty, shared-detach, and bounded growth paths; allocator failure and aliased source after release excluded'}


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('binary')
    parser.add_argument('--cases', type=int, default=512)
    args = parser.parse_args()
    print(json.dumps(run(args.binary, args.cases)))
