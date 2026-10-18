"""Check portable startup arithmetic against Python's arbitrary precision integers."""
import argparse
import json
import random
import struct

from tools.cell_corpus import verify as compare

MASK = (1 << 128)-1


def words(value):
    return [(value >> shift) & 0xffffffff for shift in (0, 32, 64, 96)]


def cases():
    rng = random.Random(0x53a1f0)
    values = [0, 1, MASK, 1 << 127, (1 << 127)-1]
    for bit in (31, 32, 52, 53, 63, 64, 95, 96, 126):
        values.extend(((1 << bit)-1, 1 << bit, (1 << bit)+1, (1 << bit)+3))
    values.extend(rng.getrandbits(128) for _ in range(512))
    for index, value in enumerate(values):
        other = values[-index-1]
        signed = value if value < 1 << 127 else value-(1 << 128)
        shift = (0, 1, 31, 32, 33, 63, 64, 65, 95, 96, 127, 128, 129)[index % 13]
        results = (value+other, value-other, value*other, value&other,
                   value << shift, signed >> shift, -value)
        for mode, result in enumerate(results):
            yield dict(input=[mode, *words(value), *words(other), shift],
                       output=words(result & MASK))
        bits = struct.unpack('<Q', struct.pack('<d', float(signed)))[0]
        yield dict(input=[7, *words(value), *words(other), shift],
                   output=[bits & 0xffffffff, bits >> 32])
    # Cross every word/bit boundary with both signs; random shift selection
    # alone is too weak for arithmetic sign extension and high carries.
    for value in (MASK, 1 << 127, (1 << 127)-1, 0x123456789abcdef0123456789abcdef):
        signed = value if value < 1 << 127 else value-(1 << 128)
        for shift in range(130):
            for mode, result in ((4, value << shift), (5, signed >> shift)):
                yield dict(input=[mode, *words(value), *words(0), shift],
                           output=words(result & MASK))


def verify(runner):
    result = compare(runner, list(cases()), 'portable startup wide integer')
    result['scope'] = 'portable startup arithmetic against Python integers and binary64 conversion'
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('runner')
    print(json.dumps(verify(parser.parse_args().runner)))
