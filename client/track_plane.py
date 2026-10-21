"""Track surface plane construction from the original routine 0x42dc50."""
import math
import struct

from .tire_response import f32


def _cross(left, right):
    # The native x87 routine keeps extended intermediates and rounds each
    # component only when it stores the output vector.
    return tuple(f32(a * b - c * d) for a, b, c, d in (
        (left[1], right[2], left[2], right[1]),
        (left[2], right[0], left[0], right[2]),
        (left[0], right[1], left[1], right[0]),
    ))


def _unit(vector):
    squared = vector[2] * vector[2] + vector[1] * vector[1] + vector[0] * vector[0]
    if squared == 0.0:
        return vector, False
    inverse = 1.0 / math.sqrt(squared)
    return tuple(f32(component * inverse) for component in vector), True


def track_plane(query_x, query_z, vertices):
    """Return (reference point, normal) for a four-corner surface quad.

    ``vertices`` are the native query fields [4..7]: p4, p5, p6, p7.
    The native routine chooses the first triangle when the X/Z edge tests
    contain the query and otherwise uses its second-triangle fallback.
    """
    if len(vertices) != 4 or any(len(point) != 3 for point in vertices):
        raise ValueError('four three-dimensional surface vertices are required')
    p4, p5, p6, p7 = tuple(tuple(f32(value) for value in point)
                            for point in vertices)
    x, z = f32(query_x), f32(query_z)
    first = (
        (p4[0] - p5[0]) * (z - p5[2]) <= (p4[2] - p5[2]) * (x - p5[0]) and
        (z - p7[2]) * (p5[0] - p7[0]) <= (x - p7[0]) * (p5[2] - p7[2]) and
        (z - p4[2]) * (p7[0] - p4[0]) <= (x - p4[0]) * (p7[2] - p4[2])
    )
    if first:
        left = tuple(a - b for a, b in zip(p4, p5))
        right = tuple(a - b for a, b in zip(p7, p5))
        normal, nonzero = _unit(_cross(left, right))
        if nonzero:
            return p5, normal

    left = tuple(a - b for a, b in zip(p6, p7))
    right = tuple(a - b for a, b in zip(p5, p7))
    normal, _ = _unit(_cross(left, right))
    return p5, normal


def _read_point(data, offset):
    return struct.unpack_from('<3f', data, offset)


def plane_from_query_record(record, *, read_memory, path_rows=None):
    """Memory-image adapter for the native 0x42dc50 query record.

    Triangle records carry pointers at +0x10..+0x1c and integer X/Z query
    coordinates at +0x20/+0x28. Row records (field +0x0c == 0) return their
    path point and intentionally leave the caller's normal untouched; callers
    that need that branch must supply the referenced path row.
    """
    if len(record) < 0x2c or not callable(read_memory):
        raise ValueError('query record must contain fields through +0x28')
    mode = struct.unpack_from('<I', record, 0x0c)[0]
    if mode == 0:
        if path_rows is None:
            raise ValueError('row-mode plane lookup requires path rows')
        index = struct.unpack_from('<I', record, 0)[0]
        row = path_rows[index]
        return tuple(_read_point(row, 0)), None
    pointers = struct.unpack_from('<4I', record, 0x10)
    points = tuple(struct.unpack('<3f', read_memory(pointer, 12))
                   for pointer in pointers)
    x = float(struct.unpack_from('<i', record, 0x20)[0])
    z = float(struct.unpack_from('<i', record, 0x28)[0])
    return track_plane(x, z, points)


def surface_height(normal, reference_point, query_point):
    """Port the x87 expression in native height helper 0x4b71a0."""
    if len(normal) != 3 or len(reference_point) != 3 or len(query_point) != 3:
        raise ValueError('height sampling requires three-dimensional vectors')
    nx, ny, nz = normal
    rx, ry, rz = reference_point
    qx, _, qz = query_point
    numerator = (qx - rx) * nx + (qz - rz) * nz
    if ny == 0.0:
        # x87 DIV with a zero denominator yields NaN for 0/0 and signed
        # infinity otherwise; the caller's comparisons and stores observe it.
        if numerator == 0.0:
            quotient = math.nan
        else:
            sign = math.copysign(1.0, numerator) * math.copysign(1.0, ny)
            quotient = math.copysign(math.inf, sign)
    else:
        quotient = numerator / ny
    return ry - quotient


def float32_ieee(value):
    """Round to native float32 while preserving IEEE NaN and infinities."""
    try:
        return struct.unpack('<f', struct.pack('<f', value))[0]
    except (OverflowError, struct.error):
        return math.copysign(math.inf, value)
