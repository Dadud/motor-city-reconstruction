"""World-grid atlas pointer fixups recovered from original 0x552a00/0x5529a0."""
from dataclasses import dataclass
import math
import struct

from .tire_response import f32


HEADER_SIZE = 0x10
TABLE_SIZE = 0x10000
TABLE_GROUPS = TABLE_SIZE // 16
PAYLOAD_OFFSET = HEADER_SIZE + TABLE_SIZE
SENTINEL = 0xDEADBEEF
_MAX_EXPANDED_WORDS = 8_000_000
_MAX_RECURSION = 64


@dataclass(frozen=True)
class WorldGridFixup:
    bounds: tuple[float, float, float, float]
    scale_x: float
    scale_y: float
    table: bytes
    payload: bytes
    cursor_address: int


def fixup_world_grid(image, image_address):
    """Relocate the 64x64 table and recursively linked payload after mesh data.

    Input begins with the four-float bounds and 16-bit-word table. The native
    routine copies the table to global state, rewrites its pointer/count cells,
    and patches payload nodes in place. This adapter returns those two mutated
    images while leaving the caller's source buffer unchanged.
    """
    if not isinstance(image, (bytes, bytearray, memoryview)):
        raise TypeError('world-grid image must be bytes-like')
    if len(image) < PAYLOAD_OFFSET:
        raise ValueError('world-grid bounds or 64 KiB pointer table is truncated')
    if type(image_address) is not int or not 0 < image_address <= 0xFFFFFFFF:
        raise ValueError('world-grid base address must be a non-null uint32')
    if image_address + len(image) > 0x100000000:
        raise ValueError('world-grid image exceeds the 32-bit address space')

    bounds = struct.unpack_from('<4f', image, 0)
    if not all(math.isfinite(value) for value in bounds):
        raise ValueError('world-grid bounds must be finite')
    width_x = bounds[2] - bounds[0]
    width_y = bounds[3] - bounds[1]
    if width_x == 0.0 or width_y == 0.0:
        raise ValueError('world-grid bounds must have nonzero width and height')
    scale_x = f32(65536.0 / width_x)
    scale_y = f32(65536.0 / width_y)

    table = bytearray(image[HEADER_SIZE:PAYLOAD_OFFSET])
    payload = bytearray(image[PAYLOAD_OFFSET:])
    table_address = image_address + HEADER_SIZE
    cursor = image_address + PAYLOAD_OFFSET
    expanded_words = 0

    def word(buffer, offset):
        if offset < 0 or offset + 4 > len(buffer):
            raise ValueError('world-grid pointer node extends past supplied payload')
        return struct.unpack_from('<I', buffer, offset)[0]

    def put(buffer, offset, value):
        if not 0 <= value <= 0xFFFFFFFF:
            raise ValueError('world-grid pointer or count exceeds uint32')
        struct.pack_into('<I', buffer, offset, value)

    def reserve_words(count):
        nonlocal cursor, expanded_words
        if count > _MAX_EXPANDED_WORDS - expanded_words:
            raise ValueError('world-grid expanded payload exceeds its bound')
        expanded_words += count
        end = cursor + count * 4
        if end > image_address + len(image) or end > 0x100000000:
            raise ValueError('world-grid expanded payload extends past supplied image')
        cursor = end

    def payload_offset(address, size=4):
        start = address - (image_address + PAYLOAD_OFFSET)
        if start < 0 or start + size > len(payload):
            raise ValueError('world-grid payload reference is outside the supplied image')
        return start

    def fix_node(address, depth):
        if depth > _MAX_RECURSION:
            raise ValueError('world-grid pointer nesting exceeds its bound')
        node = payload_offset(address, 16)
        reserve_words(4)
        tag = word(payload, node)
        if tag == SENTINEL:
            count = word(payload, node + 4)
            if count:
                put(payload, node + 8, cursor)
                reserve_words(count)
            return cursor

        for slot in range(4):
            count = word(payload, node + slot * 4)
            if count:
                child_address = cursor
                put(payload, node + slot * 4, child_address)
                cursor_after_child = fix_node(child_address, depth + 1)
                if cursor_after_child != cursor:
                    raise AssertionError('nested world-grid cursor did not advance monotonically')
        return cursor

    for group in range(TABLE_GROUPS):
        base = group * 16
        if word(table, base) == SENTINEL:
            count = word(table, base + 4)
            if count:
                put(table, base + 8, cursor)
                reserve_words(count)
            continue
        for slot in range(4):
            offset = base + slot * 4
            count = word(table, offset)
            if count:
                node_address = cursor
                put(table, offset, node_address)
                fix_node(node_address, 0)

    return WorldGridFixup(bounds, scale_x, scale_y, bytes(table), bytes(payload), cursor)
