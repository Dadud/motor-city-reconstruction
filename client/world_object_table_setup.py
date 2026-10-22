"""Portable translation of the 0x428710 world-object table preparation loop."""
import struct

from .world_object_array import WORLD_OBJECT_STRIDE


SOURCE_ROW_STRIDE = 0x38
SOURCE_POINTER_OFFSET = 0x20
COPIED_DESCRIPTOR_SIZE = 0xA8
OBJECT_DESCRIPTOR_OFFSET = 0x418


def prepare_world_object_table(objects, source_rows, source_records, *,
                               object_base_address, initialize_body):
    """Copy each source descriptor into its object and replace the source ptr.

    ``objects`` is the contiguous 0x4f8-byte object array. ``source_rows`` is
    the caller-owned 0x38-byte row table; each row's +0x20 pointer selects an
    entry in ``source_records``. ``initialize_body`` is the explicit
    0x426d50 initializer boundary and receives a mutable record image.
    """
    if not isinstance(objects, bytearray) or len(objects) % WORLD_OBJECT_STRIDE:
        raise ValueError('world object storage must contain complete 0x4f8-byte rows')
    count = len(objects) // WORLD_OBJECT_STRIDE
    if not isinstance(source_rows, bytearray) or len(source_rows) < count * SOURCE_ROW_STRIDE:
        raise ValueError('source row table is shorter than the object count')
    if not isinstance(source_records, dict):
        raise TypeError('source records must be keyed by their observed addresses')
    if type(object_base_address) is not int or not 0 <= object_base_address <= 0xffffffff:
        raise ValueError('object array base must be a uint32 address')
    if not callable(initialize_body):
        raise TypeError('the 0x426d50 body initializer is required')

    for index in range(count):
        row_offset = index * SOURCE_ROW_STRIDE
        source_address = struct.unpack_from('<I', source_rows,
                                            row_offset + SOURCE_POINTER_OFFSET)[0]
        source = source_records.get(source_address)
        if source is None or len(source) < COPIED_DESCRIPTOR_SIZE:
            raise ValueError(f'missing 0xa8-byte source descriptor at {source_address:#x}')

        object_offset = index * WORLD_OBJECT_STRIDE
        record = bytearray(objects[object_offset:object_offset + WORLD_OBJECT_STRIDE])
        descriptor_start = OBJECT_DESCRIPTOR_OFFSET
        record[descriptor_start:descriptor_start + COPIED_DESCRIPTOR_SIZE] = source[:COPIED_DESCRIPTOR_SIZE]
        struct.pack_into('<I', record, 0x4C0, 0)
        record[0x4C8:0x4EC] = bytes(0x24)
        initialize_body(record)
        objects[object_offset:object_offset + WORLD_OBJECT_STRIDE] = record
        struct.pack_into('<I', source_rows, row_offset + SOURCE_POINTER_OFFSET,
                         object_base_address + object_offset)
    return objects
