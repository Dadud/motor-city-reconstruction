"""Pointer fixups for loaded world-data sections at original 0x428680."""
import struct


_MAX_RECORDS = 100000


def layout_pointer_record_section(image, image_address, descriptor_address,
                                  cursor_address):
    """Apply the 0x428680 cursor and pointer layout to a section descriptor.

    The descriptor starts with a record count. For a nonzero count its second
    word receives the record-table address. Each 0x38-byte row contains a
    variable byte payload, a vertex count, and a triangle count; pointers are
    laid out in the original order and the cursor receives the final aligned
    address. Payload bytes themselves remain caller-supplied.
    """
    if not isinstance(image, bytearray):
        raise ValueError('world-data image must be mutable')
    if type(image_address) is not int or not 0 < image_address <= 0xffffffff:
        raise ValueError('world-data image address must be a non-null uint32')
    if type(descriptor_address) is not int or not 0 <= descriptor_address <= 0xffffffff:
        raise ValueError('descriptor address must be uint32')
    if type(cursor_address) is not int or not 0 <= cursor_address <= 0xffffffff:
        raise ValueError('cursor address must be uint32')

    def offset(address, size):
        start = address - image_address
        if start < 0 or start + size > len(image):
            raise ValueError('world-data access is outside the supplied image')
        return start

    descriptor = offset(descriptor_address, 8)
    count, = struct.unpack_from('<I', image, descriptor)
    if count == 0:
        return {'image': image, 'record_address': None,
                'cursor_address': cursor_address, 'record_count': 0}
    if count > _MAX_RECORDS:
        raise ValueError('world-data record count exceeds the bounded layout limit')
    record_bytes = count * 0x38
    table_offset = offset(cursor_address, record_bytes)
    struct.pack_into('<I', image, descriptor + 4, cursor_address)
    cursor = cursor_address + record_bytes
    if cursor > 0xffffffff:
        raise ValueError('record table cursor overflows uint32')
    for index in range(count):
        row_address = cursor_address + index * 0x38
        row = table_offset + index * 0x38
        payload_bytes, = struct.unpack_from('<I', image, row + 0x1c)
        if payload_bytes == 0:
            struct.pack_into('<I', image, row + 0x20, 0)
        else:
            struct.pack_into('<I', image, row + 0x20, cursor)
            cursor += payload_bytes
        vertex_count, = struct.unpack_from('<I', image, row + 0x24)
        struct.pack_into('<I', image, row + 0x28, cursor)
        cursor += vertex_count * 12
        struct.pack_into('<I', image, row + 0x2c, cursor)
        cursor += vertex_count * 4
        triangle_count, = struct.unpack_from('<I', image, row + 0x30)
        struct.pack_into('<I', image, row + 0x34, cursor)
        cursor += triangle_count * 0x1e
        if triangle_count & 1:
            cursor += 2
        if cursor > 0xffffffff:
            raise ValueError('world-data cursor overflows uint32')
    return {'image': image, 'record_address': cursor_address,
            'cursor_address': cursor, 'record_count': count}
