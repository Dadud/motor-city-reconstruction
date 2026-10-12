"""FRD spatial index layout recovered from native 0x552a00/0x5529a0.

Leaf identifiers are preserved without assigning collision semantics.
"""
from dataclasses import dataclass
import math
import struct


@dataclass(frozen=True)
class Node:
    identifiers: tuple[int, ...] | None
    children: tuple


@dataclass(frozen=True)
class SpatialIndex:
    bounds: tuple[float, ...]
    cells: tuple[Node, ...]

    def candidates(self, x, z):
        """Look up leaf IDs using native 0x552880 grid/quadrant ordering.

        Empty/outside cells return no candidates. IDs are still opaque.
        """
        if not math.isfinite(x) or not math.isfinite(z):
            raise ValueError('non-finite spatial query')
        xmin, zmin, xmax, zmax = self.bounds
        # Assembly stores scaled coordinates as float32 before FISTP. Use
        # nearest-even conversion; the original runtime control word is unknown.
        def scaled(value, minimum, maximum):
            value = (value-minimum)*65536/(maximum-minimum)
            if not math.isfinite(value) or abs(value) > 2**31-1:
                return -2**31
            return round(struct.unpack('<f', struct.pack('<f', value))[0])
        ix = scaled(x, xmin, xmax)
        iz = scaled(z, zmin, zmax)
        row, column = ix >> 10, iz >> 10
        if not (0 <= row < 64 and 0 <= column < 64):
            return ()
        current = self.cells[row*64+column]
        for bit in (9, 8):
            if current.identifiers is not None:
                return current.identifiers
            quadrant = ((ix >> bit) & 1) + 2*((iz >> bit) & 1)
            current = current.children[quadrant]
            if current is None:
                return ()
        if current.identifiers is None:
            raise ValueError('FRD spatial query exceeds native tree depth')
        return current.identifiers


def decode_spatial(data, offset):
    cursor = offset
    nodes = 0
    identifiers = 0

    def take(size):
        nonlocal cursor
        if cursor < 0 or size < 0 or cursor + size > len(data):
            raise ValueError('FRD spatial payload extends past EOF')
        start = cursor
        cursor += size
        return start

    bounds = struct.unpack_from('<4f', data, take(16))
    if not all(math.isfinite(v) for v in bounds) or bounds[2] <= bounds[0] or bounds[3] <= bounds[1]:
        raise ValueError('invalid FRD spatial bounds')
    grid = take(4096 * 16)

    def node(record, depth=0):
        nonlocal nodes, identifiers
        nodes += 1
        if depth > 64 or nodes > 1_000_000:
            raise ValueError('FRD spatial node budget exceeded')
        words = struct.unpack_from('<4I', data, record)
        if words[0] == 0xdeadbeef:
            identifiers += words[1]
            if identifiers > 4_000_000:
                raise ValueError('FRD spatial identifier budget exceeded')
            start = take(words[1] * 4)
            values = struct.unpack_from(f'<{words[1]}I', data, start)
            return Node(values, ())
        children = []
        for present in words:
            children.append(node(take(16), depth + 1) if present else None)
        return Node(None, tuple(children))

    cells = tuple(node(grid + i * 16) for i in range(4096))
    return SpatialIndex(bounds, cells), cursor
