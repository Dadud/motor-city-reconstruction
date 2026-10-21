"""Track-side surface selector from the original helper 0x42e230."""
import struct

from .tire_response import f32


def select_surface(position, track_index, query, track_rows, surface_flags=None):
    """Return the source boolean for an object position and track query.

    ``query`` is the 0x44-byte spatial record. Its fourth dword may identify a
    surface descriptor, in which case ``surface_flags`` supplies that
    descriptor's observed byte at +4. Otherwise selection uses the supplied
    track-row position, normal, and two side bytes.
    """
    position = tuple(map(f32, position))
    if len(position) != 3:
        raise ValueError('position must have three components')
    if type(track_index) is not int or not 0 <= track_index <= 0xffffffff:
        raise ValueError('track index must be uint32')
    query = bytes(query)
    if len(query) < 0x44:
        raise ValueError('the spatial query must contain 17 dwords')
    surface_pointer = struct.unpack_from('<I', query, 12)[0]
    if surface_pointer:
        if surface_flags is None:
            raise ValueError('a non-null surface pointer requires its observed flag byte')
        if type(surface_flags) is not int or not 0 <= surface_flags <= 0xff:
            raise ValueError('surface flags must be the observed byte value')
        if surface_flags & 0x20:
            return True

    if track_index >= len(track_rows):
        raise ValueError('track index is outside the supplied row table')
    source_row = track_rows[track_index]
    if isinstance(source_row, (bytes, bytearray, memoryview)):
        raw_row = bytes(source_row)
    else:
        values = tuple(map(f32, source_row))
        if len(values) < 21:
            raise ValueError('track row must contain 21 float slots')
        raw_row = struct.pack('<21f', *values[:21])
    if len(raw_row) < 0x54:
        raise ValueError('track row must contain 0x54 bytes')
    row = struct.unpack_from('<12f', raw_row)
    displacement = tuple(f32(position[i] - row[i]) for i in range(3))
    normal = row[9:12]
    side = (displacement[0] * normal[0] + displacement[1] * normal[1] +
            displacement[2] * normal[2]) > 0.0
    side_flags = raw_row[0x50:0x52]
    return side_flags[1 if side else 0] == 2
