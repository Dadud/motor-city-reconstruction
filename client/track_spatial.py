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


def decode_relocated_spatial(bounds, table, payload, image_address):
    """Build a query index from the pointer-relocated 0x552a00 result."""
    if len(bounds) != 4 or not all(math.isfinite(v) for v in bounds):
        raise ValueError('invalid relocated spatial bounds')
    if bounds[2] <= bounds[0] or bounds[3] <= bounds[1]:
        raise ValueError('invalid relocated spatial bounds')
    if len(table) != 4096 * 16:
        raise ValueError('relocated spatial table must be exactly 64 KiB')
    if type(image_address) is not int or not 0 < image_address <= 0xffffffff:
        raise ValueError('relocated spatial base must be a non-null uint32')
    payload_base = image_address + 16 + 4096 * 16
    payload_end = payload_base + len(payload)
    nodes = 0
    identifiers = 0

    def words_at(buffer, offset):
        if offset < 0 or offset + 16 > len(buffer):
            raise ValueError('relocated spatial node extends past payload')
        return struct.unpack_from('<4I', buffer, offset)

    def node(address, depth=0):
        nonlocal nodes, identifiers
        nodes += 1
        if depth > 64 or nodes > 1_000_000:
            raise ValueError('relocated spatial node budget exceeded')
        offset = address - payload_base
        words = words_at(payload, offset)
        if words[0] == 0xdeadbeef:
            count = words[1]
            if count == 0:
                return Node((), ())
            identifiers += count
            if identifiers > 4_000_000:
                raise ValueError('relocated spatial identifier budget exceeded')
            start = words[2] - payload_base
            if start < 0 or start + count * 4 > len(payload):
                raise ValueError('relocated spatial identifiers extend past payload')
            values = struct.unpack_from(f'<{count}I', payload, start)
            return Node(values, ())
        children = []
        for pointer in words:
            if pointer and not payload_base <= pointer < payload_end:
                raise ValueError('relocated spatial child pointer is outside payload')
            children.append(node(pointer, depth + 1) if pointer else None)
        return Node(None, tuple(children))

    def root_node(offset):
        words = words_at(table, offset)
        if words[0] == 0xdeadbeef:
            count = words[1]
            if count == 0:
                return Node((), ())
            identifiers_local = words[2] - payload_base
            if identifiers_local < 0 or identifiers_local + count * 4 > len(payload):
                raise ValueError('relocated root identifiers extend past payload')
            values = struct.unpack_from(f'<{count}I', payload, identifiers_local)
            return Node(values, ())
        children = []
        for pointer in words:
            if pointer and not payload_base <= pointer < payload_end:
                raise ValueError('relocated root child pointer is outside payload')
            children.append(node(pointer, 1) if pointer else None)
        return Node(None, tuple(children))

    cells = tuple(root_node(i * 16) for i in range(4096))
    return SpatialIndex(tuple(bounds), cells)


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
