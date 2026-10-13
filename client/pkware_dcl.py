"""Bounded Python adaptation of Mark Adler's blast 1.3 PKWARE DCL decoder.

Altered source: Python implementation with explicit input/output limits.
Original: https://github.com/madler/zlib/tree/master/contrib/blast
Copyright (C) 2003, 2012, 2013 Mark Adler

This software is provided 'as-is', without any express or implied
warranty.  In no event will the author be held liable for any damages
arising from the use of this software.

Permission is granted to anyone to use this software for any purpose,
including commercial applications, and to alter it and redistribute it
freely, subject to the following restrictions:

1. The origin of this software must not be misrepresented; you must not
   claim that you wrote the original software. If you use this software
   in a product, an acknowledgment in the product documentation would be
   appreciated but is not required.
2. Altered source versions must be plainly marked as such, and must not be
   misrepresented as being the original software.
3. This notice may not be removed or altered from any source distribution.

Mark Adler    madler@alumni.caltech.edu
"""
import struct


def _table(repetitions):
    lengths = [value & 15 for value in repetitions for _ in range((value >> 4)+1)]
    counts = tuple(lengths.count(length) for length in range(14))
    symbols = tuple(sorted(range(len(lengths)), key=lambda symbol: (lengths[symbol], symbol)))
    return counts, symbols


_LITERALS = _table((11,124,8,7,28,7,188,13,76,4,10,8,12,10,12,10,8,23,8,
    9,7,6,7,8,7,6,55,8,23,24,12,11,7,9,11,12,6,7,22,5,7,24,6,11,9,6,7,
    22,7,11,38,7,9,8,25,11,8,11,9,12,8,12,5,38,5,38,5,11,7,5,6,21,6,10,
    53,8,7,24,10,27,44,253,253,253,252,252,252,13,12,45,12,45,12,61,12,45,44,173))
_LENGTHS = _table((2,35,36,53,38,23))
_DISTANCES = _table((2,20,53,230,247,151,248))
_BASE = (3,2,4,5,6,7,8,9,10,12,16,24,40,72,136,264)
_EXTRA = (0,0,0,0,0,0,0,0,1,2,3,4,5,6,7,8)


class _Bits:
    def __init__(self, data):
        self.data = data
        self.position = self.buffer = self.count = 0

    def take(self, count):
        while self.count < count:
            if self.position == len(self.data):
                raise ValueError('truncated PKWARE DCL stream')
            self.buffer |= self.data[self.position] << self.count
            self.position += 1
            self.count += 8
        value = self.buffer & ((1 << count)-1)
        self.buffer >>= count
        self.count -= count
        return value

    def symbol(self, table):
        counts, symbols = table
        code = first = index = 0
        for length in range(1, 14):
            code |= self.take(1) ^ 1
            count = counts[length]
            if code < first+count:
                return symbols[index+code-first]
            index += count
            first = (first+count) << 1
            code <<= 1
        raise ValueError('invalid PKWARE DCL Huffman code')


def explode(stream, *, max_output=65526):
    """Decode DCL with a hard output bound; bytes after the end code are ignored."""
    if not isinstance(stream, bytes) or not 2 <= len(stream) <= 65526:
        raise ValueError('expected bounded PKWARE DCL bytes')
    if type(max_output) is not int or not 0 <= max_output <= 65526:
        raise ValueError('expected bounded PKWARE DCL output size')
    bits = _Bits(stream)
    literals, dictionary = bits.take(8), bits.take(8)
    if literals not in (0, 1) or dictionary not in (4, 5, 6):
        raise ValueError('invalid PKWARE DCL header')
    output = bytearray()
    while True:
        if bits.take(1):
            symbol = bits.symbol(_LENGTHS)
            length = _BASE[symbol]+bits.take(_EXTRA[symbol])
            if length == 519:
                return bytes(output)
            extra = 2 if length == 2 else dictionary
            distance = (bits.symbol(_DISTANCES) << extra)+bits.take(extra)+1
            if distance > len(output):
                raise ValueError('PKWARE DCL distance precedes output')
            if len(output)+length > max_output:
                raise ValueError('PKWARE DCL output exceeds bound')
            for _ in range(length):
                output.append(output[-distance])
        else:
            value = bits.symbol(_LITERALS) if literals else bits.take(8)
            if len(output) == max_output:
                raise ValueError('PKWARE DCL output exceeds bound')
            output.append(value)


def decompress_mcots_payload(payload):
    """Read the native uint16 output-size prefix, then decode exactly that size."""
    if not isinstance(payload, bytes) or not 4 <= len(payload) <= 65526:
        raise ValueError('truncated or oversized compressed MCOTS payload')
    expected = struct.unpack_from('<H', payload)[0]
    if not 1 <= expected <= 65526:
        raise ValueError('invalid MCOTS decompressed size')
    output = explode(payload[2:], max_output=expected)
    if len(output) != expected:
        raise ValueError('MCOTS decompressed size differs from declared size')
    return output
