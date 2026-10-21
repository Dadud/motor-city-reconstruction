"""Track reference-frame selection from original helper 0x42df00."""
import struct

from .tire_response import f32


QUERY_BYTES = 0x44
TRACK_ROW_BYTES = 0x54


def _vec3(values):
    values = tuple(f32(value) for value in values)
    if len(values) != 3:
        raise ValueError('three-component vector required')
    return values


def track_frame(query, track_rows, referenced_point=None):
    """Return ``(reference_point, frame)`` for a 17-dword query record.

    ``track_rows`` is indexed by the query's first dword and each row contains
    21 float32 values. In the alternate branch the 13th query dword is a
    vector-storage pointer represented by ``referenced_point``; accepting the
    resolved vector keeps native addresses outside the portable record type.
    """
    query = bytes(query)
    if len(query) < QUERY_BYTES:
        raise ValueError('the 0x42df00 query must contain 17 dwords')
    words = struct.unpack_from('<17I', query)
    index, mode = words[0], words[2]
    use_track_row = words[3] == 0 or mode != 0
    if use_track_row:
        if type(index) is not int or index >= len(track_rows):
            raise ValueError('track row index is outside the supplied table')
        row = tuple(f32(value) for value in track_rows[index])
        if len(row) < 12:
            raise ValueError('track row must contain at least twelve floats')
        return row[:3], (row[9], row[10], row[11], *row[3:9])

    if referenced_point is None:
        raise ValueError('alternate query requires the referenced three-float point')
    point = _vec3(referenced_point)
    first = tuple(struct.unpack_from('<3f', query, 44))
    second = tuple(struct.unpack_from('<3f', query, 56))
    first, second = tuple(map(f32, first)), tuple(map(f32, second))
    cross = (f32(first[1] * second[2] - first[2] * second[1]),
             f32(first[2] * second[0] - first[0] * second[2]),
             f32(first[0] * second[1] - first[1] * second[0]))
    return point, (*cross, *first, *second)
