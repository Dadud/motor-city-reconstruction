"""Single-face portion of the startup projected-area rasterizer (0x4836f0)."""
import math

from .raster_intersection import raster_scanline_intersections
from .raster_rounding import raster_ceil, raster_floor
from .raster_triangle import order_triangle_vertices_by_y
from .tire_response import f32

RASTER_WIDTH = 321
RASTER_HEIGHT = 241


def rasterize_projected_triangle(vertices, x_bounds, y_bounds):
    """Project one XY triangle into the original 321x241 occupancy raster.

    ``vertices`` are model-space XY points after the caller's per-surface
    translation/reflection. Bounds are the owner's XY extents. The result is
    the face's occupancy mask; this function does not traverse scene records.
    """
    points = tuple(tuple(f32(value) for value in point) for point in vertices)
    if len(points) != 3 or any(len(point) != 2 for point in points):
        raise ValueError('exactly three 2D vertices are required')
    if len(x_bounds) != 2 or len(y_bounds) != 2:
        raise ValueError('each raster bound must contain a minimum and maximum')
    xmin, xmax = (f32(value) for value in x_bounds)
    ymin, ymax = (f32(value) for value in y_bounds)
    values = (*points[0], *points[1], *points[2], xmin, xmax, ymin, ymax)
    if not all(math.isfinite(value) for value in values):
        raise ValueError('finite float32 triangle coordinates and bounds required')
    if xmin == xmax or ymin == ymax:
        raise ValueError('projection bounds must have nonzero extents')

    scale_x = f32((320.0 / ((xmax - xmin) * 0.5)) * 0.5)
    scale_y = f32((240.0 / ((ymax - ymin) * 0.5)) * 0.5)
    projected = []
    for x, y in points:
        sx = f32((x - xmin) * scale_x)
        sy = f32((ymax - y) * scale_y)
        projected.append((min(320.0, max(0.0, sx)),
                          min(240.0, max(0.0, sy))))

    (x1, y1), (x2, y2), (x3, y3) = projected
    if ((y2 - y1) * (x3 - x1) == (y3 - y1) * (x2 - x1)):
        return bytes(RASTER_WIDTH * RASTER_HEIGHT)

    ordered = order_triangle_vertices_by_y(projected)
    low, middle, high = ordered
    first_row = raster_ceil(low[1])
    last_row = raster_floor(high[1])
    bitmap = bytearray(RASTER_WIDTH * RASTER_HEIGHT)
    for row in range(first_row, last_row + 1):
        if row < middle[1] or middle[1] == high[1]:
            edge_a = (low, middle)
            edge_b = (low, high)
        else:
            edge_a = (low, high)
            edge_b = (middle, high)
        left, right = raster_scanline_intersections(edge_a, edge_b, row)
        first_x = raster_ceil(left)
        last_x = raster_floor(right)
        offset = row * RASTER_WIDTH
        for column in range(first_x, last_x + 1):
            bitmap[offset + column] = 1
    return bytes(bitmap)
