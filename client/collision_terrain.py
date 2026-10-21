"""Terrain triangle candidate gates recovered from original 0x45a320."""
from .tire_response import f32


def triangle_candidate_gate(projected_point, vertices):
    """Return whether one supplied triangle passes the caller's early gates.

    ``projected_point`` is the object's ``(+8,+0x10)`` pair. ``vertices`` are
    the three supplied world points as XYZ triples. This covers the three
    signed XZ edge inequalities and the nonzero 3D edge-length checks made by
    ``0x6f14f0``; it does not perform candidate height/response processing.
    """
    if len(projected_point) != 2 or len(vertices) != 3 or any(len(v) != 3 for v in vertices):
        raise ValueError('one projected point and three XYZ triangle vertices are required')
    x, z = (f32(value) for value in projected_point)
    points = tuple(tuple(f32(value) for value in vertex) for vertex in vertices)

    for index in range(3):
        a = points[index]
        b = points[(index + 1) % 3]
        left = f32(f32(a[2] - b[2]) * f32(x - b[0]))
        right = f32(f32(a[0] - b[0]) * f32(z - b[2]))
        if not left <= right:
            return False

    # 0x6f14f0 returns the Euclidean length of each consecutive 3D edge;
    # the caller requires every result to be nonzero.
    for index in range(3):
        a = points[index]
        b = points[(index + 1) % 3]
        if all(a[axis] == b[axis] for axis in range(3)):
            return False
    return True
