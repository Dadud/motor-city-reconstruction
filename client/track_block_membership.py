"""Membership query over the native block-index rows."""
import struct


ROW_STRIDE = 0x6C4
ID_OFFSET = 0x190
ID_SLOT_STRIDE = 4


def contains_track_block_id(table, global_count, query_id, row_index):
    """Translate 0x42d810 over a bounded view of the global table.

    The second argument selects a row at 0x6c4-byte intervals. Within that
    row, signed 16-bit IDs occupy slots four bytes apart beginning at +0x190.
    The native loop scans slot zero through ``global_count`` inclusively. The
    assembly's scaled index also adds the row index before multiplication.
    """
    if not isinstance(table, (bytes, bytearray, memoryview)):
        raise ValueError('table must be a byte view')
    for value, name in ((global_count, 'global count'),
                        (query_id, 'query ID'), (row_index, 'row index')):
        if type(value) is not int or not -0x80000000 <= value <= 0x7fffffff:
            raise ValueError(f'{name} must be a signed 32-bit integer')
    if query_id == row_index:
        return True
    if global_count < 0:
        return False
    end = row_index * ROW_STRIDE + ID_OFFSET + global_count * ID_SLOT_STRIDE + 2
    if row_index < 0 or len(table) < end:
        raise ValueError('table is shorter than the native scan')
    for slot in range(global_count + 1):
        value = struct.unpack_from('<h', table,
                                   row_index * ROW_STRIDE + ID_OFFSET
                                   + slot * ID_SLOT_STRIDE)[0]
        if value == query_id:
            return True
    return False
