"""Reset shared track collision/query state from native routine 0x42d2e0."""
import struct


METADATA_SIZE = 0xC00
METADATA_ENTRY_SIZE = 3
BLOCK_STRIDE = 0x6C4
BLOCK_ARRAY_COUNT_OFFSET = 0x69C
BLOCK_ARRAY_POINTER_OFFSET = 0x6A0
SECONDARY_SIZE = 0x1800
SECONDARY_STRIDE = 0x18


def reset_secondary_collision_table(secondary_table):
    """Reset three dwords in each 0x18-byte row of native 0x407550."""
    if not isinstance(secondary_table, bytearray) or len(secondary_table) != SECONDARY_SIZE:
        raise ValueError('secondary table must be a mutable 0x1800-byte view')
    for row in range(SECONDARY_SIZE // SECONDARY_STRIDE):
        offset = row * SECONDARY_STRIDE
        struct.pack_into('<III', secondary_table, offset, 0, 0xFFFFFFFF, 0)
    return secondary_table


def reset_track_collision_state(metadata, block_table, block_bound,
                                pointed_arrays, secondary_table):
    """Apply the byte and word resets performed by native routine 0x42d2e0.

    All addresses are represented by explicit buffers. ``block_bound`` is
    the signed native global at 0x97dbec; a nonnegative value scans rows zero
    through that bound inclusively. Each qualifying block points to an array
    image in ``pointed_arrays`` whose first cleared word is at offset +2 and
    whose subsequent entries are 24 bytes apart.
    """
    if not isinstance(metadata, bytearray) or len(metadata) != METADATA_SIZE:
        raise ValueError('metadata must be a mutable 0xC00-byte view')
    if not isinstance(block_table, bytearray):
        raise ValueError('block table must be a mutable byte view')
    if type(block_bound) is not int or not -0x80000000 <= block_bound <= 0x7fffffff:
        raise ValueError('block bound must be signed 32-bit')
    if not isinstance(pointed_arrays, dict):
        raise ValueError('pointed arrays must map native pointer values to mutable views')
    if not isinstance(secondary_table, bytearray) or len(secondary_table) != SECONDARY_SIZE:
        raise ValueError('secondary table must be a mutable 0x1800-byte view')

    for index in range(METADATA_SIZE // METADATA_ENTRY_SIZE):
        offset = index * METADATA_ENTRY_SIZE
        metadata[offset:offset + METADATA_ENTRY_SIZE] = b'\xff\x00\x00'

    if block_bound >= 0:
        required = block_bound * BLOCK_STRIDE + BLOCK_ARRAY_POINTER_OFFSET + 4
        if len(block_table) < required:
            raise ValueError('block table is shorter than the native inclusive scan')
        for row in range(block_bound + 1):
            base = row * BLOCK_STRIDE + BLOCK_ARRAY_COUNT_OFFSET
            entry_count, pointer = struct.unpack_from('<iI', block_table, base)
            if entry_count <= 0 or pointer == 0:
                continue
            try:
                image = pointed_arrays[pointer]
            except KeyError as error:
                raise ValueError(f'missing pointed array at {pointer:#x}') from error
            if not isinstance(image, bytearray):
                raise ValueError('pointed array views must be mutable bytearrays')
            needed = 2 + (entry_count - 1) * 24 + 2
            if len(image) < needed:
                raise ValueError('pointed array is shorter than its native entry count')
            for index in range(entry_count):
                struct.pack_into('<H', image, 2 + index * 24, 0)

    reset_secondary_collision_table(secondary_table)
    return metadata, block_table, pointed_arrays, secondary_table
