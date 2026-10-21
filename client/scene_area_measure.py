"""Decoded-geometry calculation for the aggregate 0x483450 scene-area query."""
from .raster_bounds import occupied_raster_bounds
from .raster_fill import RASTER_HEIGHT, RASTER_WIDTH, rasterize_projected_triangle
from .raster_scene import _transformed_triangles, raster_meshes_from_nodes
from .tire_response import f32


def scene_area_from_geometry(meshes, *, raster_enabled=True):
    """Compute the original projected-area score from decoded surface meshes.

    This covers the body formula and input geometry semantics after scene-list
    and model-buffer decoding. Allocation and acquisition of the original
    linked scene registry remain caller responsibilities.
    """
    if not raster_enabled:
        return 0.0
    triangles = []
    min_x = min_y = f32(1_000_000.0)
    max_x = max_y = f32(-1_000_000.0)
    for triangle in _transformed_triangles(meshes):
        triangles.append(triangle)
        for x, y in triangle:
            if x < min_x:
                min_x = x
            if max_x < x:
                max_x = x
            if y < min_y:
                min_y = y
            if max_y < y:
                max_y = y

    if not triangles or min_x == max_x or min_y == max_y:
        return 0.0
    bitmap = bytearray(RASTER_WIDTH * RASTER_HEIGHT)
    for triangle in triangles:
        face = rasterize_projected_triangle(
            triangle, (min_x, max_x), (min_y, max_y))
        for index, occupied in enumerate(face):
            if occupied:
                bitmap[index] = 1
    min_px, min_py, max_px, max_py, count = occupied_raster_bounds(bitmap)
    if count == 0:
        return 0.0
    pixel_width = max_px + 1 - min_px
    pixel_height = max_py + 1 - min_py
    if pixel_width == 0 or pixel_height == 0:
        return 0.0
    numerator = ((float(max_y) - min_y) * 0.5 *
                 (float(max_x) - min_x) * 0.5 * 4.0 * count)
    return f32(numerator / (pixel_width * pixel_height))


def scene_area_from_nodes(nodes, *, raster_enabled=True):
    """Run the area calculation over decoded original scene nodes and FCEs."""
    return scene_area_from_geometry(
        raster_meshes_from_nodes(nodes), raster_enabled=raster_enabled)
