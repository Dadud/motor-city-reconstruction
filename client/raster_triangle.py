"""Triangle vertex ordering used by the startup projected-area rasterizer."""
import math

from .tire_response import f32


def order_triangle_vertices_by_y(vertices):
    """Translate 0x483c70, returning the three vertices from low to high Y.

    The explicit branches preserve the original's input-order choices for
    equal Y coordinates; a generic stable sort does not reproduce them.
    """
    points = tuple(tuple(f32(value) for value in point) for point in vertices)
    if len(points) != 3 or any(len(point) != 2 for point in points):
        raise ValueError('exactly three two-dimensional vertices are required')
    if any(not math.isfinite(value) for point in points for value in point):
        raise ValueError('finite float32 triangle coordinates required')
    (x1, y1), (x2, y2), (x3, y3) = points
    # The first low vertex wins ties, then the second. Remaining vertices use
    # the original helper's explicit equality-sensitive branch choices.
    if y1 <= y2 and y1 <= y3:
        return ((x1, y1), (x2, y2), (x3, y3)) if y2 < y3 else (
            (x1, y1), (x3, y3), (x2, y2))
    if y2 <= y3:
        return ((x2, y2), (x1, y1), (x3, y3)) if y1 <= y3 else (
            (x2, y2), (x3, y3), (x1, y1))
    return ((x3, y3), (x1, y1), (x2, y2)) if y1 < y2 else (
        (x3, y3), (x2, y2), (x1, y1))
