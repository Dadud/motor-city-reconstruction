"""Track-backed projection helpers recovered from the renderer."""
import struct


def track_point_without_cached_geometry(track_rows, track_index,
                                        context_flags):
    """Return the track row XYZ copied by 0x42dc50 when context[3] is zero."""
    if (not isinstance(track_rows,(tuple,list)) or not track_rows or
        any(not isinstance(row,(bytes,bytearray)) or len(row)!=0x54
            for row in track_rows)):
        raise ValueError('track rows must be nonempty 0x54-byte records')
    if type(track_index) is not int or not 0<=track_index<len(track_rows):
        raise ValueError('track index is outside the supplied rows')
    if type(context_flags) is not int or not 0<=context_flags<=0xffffffff:
        raise ValueError('projection context flag must be an unsigned word')
    if context_flags:
        raise ValueError('cached-geometry contexts are outside this translation')
    return struct.unpack_from('<3f',track_rows[track_index],0)
