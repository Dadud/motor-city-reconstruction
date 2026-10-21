"""Projected triangle edge intersections for one startup raster scanline."""
import math

from .tire_response import f32


def raster_scanline_intersections(edge_a, edge_b, scan_y):
    """Translate 0x483e80 and return (leftmost_x, rightmost_x).

    Each edge is ``((x1, y1), (x2, y2))``. Horizontal edges are outside the
    caller's supported domain; the original divides by their zero Y span.
    """
    a = tuple(f32(value) for point in edge_a for value in point)
    b = tuple(f32(value) for point in edge_b for value in point)
    y = f32(scan_y)
    if len(a) != 4 or len(b) != 4:
        raise ValueError('each edge must contain exactly two 2D points')
    if not all(math.isfinite(value) for value in (*a, *b, y)):
        raise ValueError('finite float32 edge coordinates required')
    x1, y1, x2, y2 = a
    x3, y3, x4, y4 = b
    if y2 == y1 or y4 == y3:
        raise ValueError('horizontal edges have undefined intersection')
    first = f32(((y - y1) * (x2 - x1)) / (y2 - y1) + x1)
    second = f32(((y - y3) * (x4 - x3)) / (y4 - y3) + x3)
    return (min(first, second), max(first, second))
