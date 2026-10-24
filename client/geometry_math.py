"""Small geometric predicates recovered from the MCO client math library."""
import math
import struct


def _float32(value):
    """Round one finite Python number to the binary32 input type."""
    try:
        return struct.unpack('<f', struct.pack('<f', value))[0]
    except (OverflowError, struct.error) as exc:
        raise ValueError('oriented area inputs must fit finite binary32') from exc


def rounded_oriented_area2(point_a, point_b, point_c):
    """Translate 0x6f2da0's rounded 2D oriented-area determinant.

    The float inputs are binary32 coordinates. Python's ``round`` reproduces
    the native x87 default round-to-nearest, ties-to-even conversion for the
    finite in-range results represented here.
    """
    points = tuple(tuple(point) for point in (point_a, point_b, point_c))
    if any(len(point) != 2 or any(not math.isfinite(value) for value in point)
           for point in points):
        raise ValueError('oriented area requires three finite 2D points')
    points = tuple(tuple(_float32(value) for value in point) for point in points)
    a, b, c = points
    # The original keeps the cross product in x87 precision, spills it to a
    # stack float, then reloads that binary32 value for FISTP.
    determinant = ((b[0] - a[0]) * (c[1] - a[1]) -
                   (c[0] - a[0]) * (b[1] - a[1]))
    determinant = _float32(determinant)
    result = round(determinant)
    if not -(1 << 31) <= result < (1 << 31):
        raise ValueError('oriented area result is outside native int32 range')
    return result
