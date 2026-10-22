"""Vertex-to-plane world contact response recovered from original 0x459940."""
from dataclasses import dataclass, replace
import math
import struct

from client.collision_pair_response import (CollisionImpactBody,
                                            resolve_surface_impulse)
from client.geometry_transform import add_vector_to_points, transform_vertices
from client.tire_response import f32


def _dot(a, b):
    return f32(f32(f32(a[0] * b[0]) + f32(a[1] * b[1])) + f32(a[2] * b[2]))


@dataclass(frozen=True)
class WorldVertexContactResult:
    collided: bool
    body: CollisionImpactBody
    point: tuple[float, float, float] | None
    penetration: float
    selected_vertex: int | None


def resolve_world_vertex_contact(body, local_vertices, normal, plane_point,
                                max_distance, threshold_coefficient,
                                sliding_coefficient):
    """Translate the 8/22 vertex plane scan and response call in 0x459940.

    ``local_vertices`` are the points returned by the preceding body-specific
    geometry extractor. The 8-point extraction itself remains a separate
    unresolved branch; count=22 corresponds to the ordinary cached geometry
    path and is the path exercised by the shipped-client comparison.
    """
    if not isinstance(body, CollisionImpactBody):
        raise ValueError('a collision impact body is required')
    vertices = tuple(f32(value) for value in local_vertices)
    normal = tuple(f32(value) for value in normal)
    plane_point = tuple(f32(value) for value in plane_point)
    if len(vertices) not in (24, 66) or len(normal) != 3 or len(plane_point) != 3:
        raise ValueError('expected 8 or 22 local points and two 3D vectors')
    if not all(math.isfinite(value)
               for value in (*vertices, *normal, *plane_point, max_distance)):
        raise ValueError('world contact inputs must be finite')
    if len(body.contact_record) < 0x400:
        raise ValueError('collision body image must span at least 0x400 bytes')

    count = len(vertices) // 3
    matrix = body.inertia.body_to_world
    transformed = transform_vertices(vertices, matrix, body.position, count=count)
    best = f32(max_distance)
    selected = None
    selected_point = None
    for index in range(count):
        point = transformed[index * 3:index * 3 + 3]
        plane_distance = _dot(tuple(f32(point[axis] - plane_point[axis])
                                    for axis in range(3)), normal)
        body_distance = _dot(tuple(f32(point[axis] - body.position[axis])
                                   for axis in range(3)), normal)
        if plane_distance < best and body_distance < 0.0:
            best, selected, selected_point = plane_distance, index, point

    if selected is None or not best < f32(max_distance):
        return WorldVertexContactResult(False, body, None, 0.0, None)

    point_from_plane = tuple(f32(selected_point[axis] - plane_point[axis])
                             for axis in range(3))
    penetration = _dot(point_from_plane, normal)
    if penetration < 0.0:
        amount = f32(-penetration)
        correction = tuple(f32(normal[axis] * amount) for axis in range(3))
        position = tuple(f32(body.position[axis] + correction[axis]) for axis in range(3))
        selected_point = tuple(f32(selected_point[axis] + correction[axis])
                               for axis in range(3))
        data = bytearray(body.contact_record)
        cached = struct.unpack_from('<66f', data, 0x1e8)
        struct.pack_into('<66f', data, 0x1e8,
                         *add_vector_to_points(cached, correction, count=22))
        body = replace(body, position=position, contact_record=bytes(data))
        penetration = f32(penetration)

    impact = resolve_surface_impulse(body, selected_point, normal,
                                     threshold_coefficient, sliding_coefficient)
    return WorldVertexContactResult(impact.collided, impact.body,
                                    selected_point, penetration, selected)
