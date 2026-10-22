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


@dataclass(frozen=True)
class ExtractedWorldContactPoints:
    count: int
    vertices: tuple[float, ...]


def extract_world_contact_points(body_image):
    """Translate the compact/full body point extractor at original 0x4596b0."""
    image = bytes(body_image)
    if len(image) < 0x1e8:
        raise ValueError('body image must cover the 22-point local geometry buffer')
    compact = (struct.unpack_from('<h', image, 0x3bc)[0] == 0 and
               abs(struct.unpack_from('<f', image, 0xc4)[0]) > .707)
    if not compact:
        return ExtractedWorldContactPoints(
            22, struct.unpack_from('<66f', image, 0xe0))

    value = lambda offset: struct.unpack_from('<f', image, offset)[0]
    choose_left_if_less = lambda left, right: left if left < right else right
    choose_right_if_less = lambda left, right: right if left < right else left
    average = lambda left, right: f32((left + right) * .5)
    vertices = (
        choose_left_if_less(value(0xe0), value(0x110)),
        average(value(0xe4), value(0x114)),
        choose_right_if_less(value(0xe8), value(0x118)),
        choose_right_if_less(value(0xec), value(0x11c)),
        average(value(0x120), value(0xf0)),
        choose_right_if_less(value(0xf4), value(0x124)),
        choose_right_if_less(value(0xf8), value(0x128)),
        average(value(0x12c), value(0xfc)),
        choose_left_if_less(value(0x100), value(0x130)),
        choose_left_if_less(value(0x104), value(0x134)),
        average(value(0x138), value(0x108)),
        choose_left_if_less(value(0x10c), value(0x13c)),
        *struct.unpack_from('<12f', image, 0x140),
    )
    return ExtractedWorldContactPoints(8, tuple(f32(value) for value in vertices))


def apply_world_decision_two_contact_cache(body_image, decision, type_code,
                                          sample_position):
    """Translate the ``iVar2 == 2`` contact-cache branch in 0x45d1f0."""
    image = bytes(body_image)
    point = tuple(f32(value) for value in sample_position)
    if len(image) < 0x400 or len(point) != 3:
        raise ValueError('a 0x400-byte body image and 3D sample point are required')
    if (type(decision) is not int or type(type_code) is not int or
            type_code < 0 or type_code > 0xffffffff):
        raise ValueError('decision and type code are outside their native ranges')
    if not all(math.isfinite(value) for value in point):
        raise ValueError('sample position must be finite')
    if decision != 2 or not 2.0 < struct.unpack_from('<f', image, 0x3b4)[0]:
        return image

    result = bytearray(image)
    struct.pack_into('<I', result, 0x3c4, 0)
    struct.pack_into('<f', result, 0x3c8,
                     f32(struct.unpack_from('<f', image, 0x50)[0] * 15.0))
    struct.pack_into('<3f', result, 0x3cc, 0.0, 0.0, 0.0)
    struct.pack_into('<f', result, 0x3e8, point[0])
    struct.pack_into('<f', result, 0x3ec, struct.unpack_from('<f', image, 0x0c)[0])
    struct.pack_into('<f', result, 0x3f0, point[2])
    struct.pack_into('<I', result, 0x3f4, 5)
    struct.pack_into('<I', result, 0x3f8, type_code)
    return bytes(result)


def resolve_world_vertex_contact(body, local_vertices, normal, plane_point,
                                max_distance, threshold_coefficient,
                                sliding_coefficient):
    """Translate the 8/22 vertex plane scan and response call in 0x459940.

    ``local_vertices`` are the points returned by
    :func:`extract_world_contact_points` for the same body image.
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
