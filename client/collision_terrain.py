"""Terrain triangle gates recovered from original 0x45a320."""
from dataclasses import dataclass
import math

from .collision_impulse import plane_height
from .track_plane import plane_from_query_record
from .track_surface_lookup import TrackSurfaceWorld, track_surface_lookup
from .tire_response import f32


# Decoded uint32 triangle-index tables read from mcity.exe's shape dispatch:
# 0x88c9d4 (shapes 0/2), 0x88ca64 (shape 1), and 0x88c7f4 (shapes 3/4).
_SHAPE_0_2_TRIANGLES = (
    (0, 4, 5), (5, 1, 0), (5, 6, 2), (5, 2, 1),
    (6, 7, 3), (6, 3, 2), (7, 4, 0), (7, 0, 3),
    (0, 1, 2), (0, 2, 3), (5, 4, 7), (5, 7, 6),
)
_SHAPE_1_TRIANGLES = (
    (0, 1, 3), (1, 2, 3), (12, 1, 0), (12, 2, 1),
    (12, 3, 2), (12, 0, 3),
)
_SHAPE_3_4_TRIANGLES = (
    (18, 1, 13), (1, 19, 13), (19, 2, 13), (2, 21, 13),
    (21, 3, 13), (3, 20, 13), (20, 0, 13), (0, 18, 13),
    (5, 14, 12), (14, 4, 12), (4, 16, 12), (16, 7, 12),
    (7, 17, 12), (17, 6, 12), (6, 15, 12), (15, 5, 12),
    (4, 14, 8), (14, 5, 8), (5, 1, 8), (1, 18, 8),
    (18, 0, 8), (0, 4, 8), (6, 17, 9), (17, 7, 9),
    (7, 3, 9), (3, 21, 9), (21, 2, 9), (2, 6, 9),
    (5, 15, 11), (15, 6, 11), (6, 2, 11), (2, 19, 11),
    (19, 1, 11), (1, 5, 11), (7, 16, 10), (16, 4, 10),
    (4, 0, 10), (0, 20, 10), (20, 3, 10), (3, 7, 10),
)


def terrain_shape_triangle_indices(shape):
    """Return the original ordered triangle-index list for collision shape."""
    if type(shape) is not int:
        raise ValueError('terrain collision shape must be an integer')
    if shape in (0, 2):
        return _SHAPE_0_2_TRIANGLES
    if shape == 1:
        return _SHAPE_1_TRIANGLES
    if shape in (3, 4):
        return _SHAPE_3_4_TRIANGLES
    raise ValueError(f'unsupported terrain collision shape {shape}')


def terrain_shape_triangles(shape, vertices):
    """Expand the shape's recovered index list over its supplied mesh."""
    if len(vertices) != 22 or any(len(vertex) != 3 for vertex in vertices):
        raise ValueError('terrain collision mesh requires 22 XYZ vertices')
    return tuple(tuple(vertices[index] for index in triangle)
                 for triangle in terrain_shape_triangle_indices(shape))


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


def projected_shape_candidates(shape, projected_point, vertices):
    """Return ordered mesh triangles that pass the original early gates."""
    indices = terrain_shape_triangle_indices(shape)
    if len(vertices) != 22 or any(len(vertex) != 3 for vertex in vertices):
        raise ValueError('terrain collision mesh requires 22 XYZ vertices')
    candidates = []
    for ordinal, triangle in enumerate(indices):
        points = tuple(tuple(f32(value) for value in vertices[index])
                       for index in triangle)
        if triangle_candidate_gate(projected_point, points):
            candidates.append((ordinal, triangle, points))
    return tuple(candidates)


def specialized_quad_projection_gate(projected_point, vertices):
    """Translate the projected four-corner gate in ``0x54f0e0``.

    The routine splits the transformed quad along the 0-to-2 diagonal and
    continues when the projected object point lies strictly inside either
    triangle. Coordinates are the transformed world-space XZ pairs. As in the
    original, points on the tested edges are rejected by the inclusive
    ``<=`` edge predicates.
    """
    if len(projected_point) != 2 or len(vertices) != 4 or any(len(v) != 3 for v in vertices):
        raise ValueError('one projected point and four XYZ corners are required')
    x, z = (f32(value) for value in projected_point)
    points = tuple((f32(vertex[0]), f32(vertex[2])) for vertex in vertices)

    def outside(a, b):
        left = f32(f32(z - b[1]) * f32(a[0] - b[0]))
        right = f32(f32(x - b[0]) * f32(a[1] - b[1]))
        return left <= right

    a, b, c, d = points
    first = not (outside(a, b) or outside(b, c) or outside(c, a))
    second = not (outside(a, c) or outside(c, d) or outside(d, a))
    return first or second


def terrain_response_normal(vertices):
    """Recover the upward-facing response normal from three accepted points.

    This is the point-array helper `0x459e30`: its first normalized edge pair
    is tried first, followed by the two alternate edge pairs when its cross
    product has zero length. Degenerate inputs retain the source's zero vector.
    """
    if len(vertices) != 3 or any(len(vertex) != 3 for vertex in vertices):
        raise ValueError('three XYZ points are required')
    points = tuple(tuple(f32(value) for value in vertex) for vertex in vertices)

    def difference(left, right):
        return tuple(f32(left[i] - right[i]) for i in range(3))

    def normalize(vector):
        squared = f32((vector[2] * vector[2] + vector[1] * vector[1]) +
                      vector[0] * vector[0])
        if squared == 0.:
            return vector
        length = f32(math.sqrt(squared))
        inverse = f32(1. / length)
        return tuple(f32(value * inverse) for value in vector)

    def cross(left, right):
        return (f32(left[1] * right[2] - left[2] * right[1]),
                f32(left[2] * right[0] - left[0] * right[2]),
                f32(left[0] * right[1] - left[1] * right[0]))

    def nonzero(vector):
        return any(value != 0. for value in vector)

    p0, p1, p2 = points
    edge_a = normalize(difference(p0, p1))
    edge_b = normalize(difference(p0, p2))
    normal = cross(edge_a, edge_b)
    if not nonzero(normal):
        edge_a = normalize(difference(p0, p1))
        edge_b = normalize(difference(p1, p2))
        normal = cross(edge_a, edge_b)
        if not nonzero(normal):
            edge_a = normalize(difference(p1, p2))
            edge_b = normalize(difference(p0, p2))
            normal = cross(edge_a, edge_b)

    normal = normalize(normal)
    if normal[1] < 0.:
        normal = tuple(f32(-value) for value in normal)
    return normal


@dataclass(frozen=True)
class TerrainCandidateHeightResult:
    heights: tuple
    gaps: tuple
    minimum_gap: float
    accepted: bool


@dataclass(frozen=True)
class TerrainCandidateSamplingResult:
    candidate: TerrainCandidateHeightResult
    query_records: tuple
    normals: tuple


@dataclass(frozen=True)
class TerrainContactVelocityResult:
    point_velocity_dots: tuple
    predicted_gaps: tuple
    accepted_indices: tuple
    candidate_accepted: bool


@dataclass(frozen=True)
class TerrainImpactResult:
    linear_velocity: tuple
    angular_turn_velocity: tuple
    response_status: int
    tangential_impulse: tuple
    applied: bool


def triangle_candidate_height_gate(vertices, surface_heights, object_heights):
    """Translate the candidate's three height fallbacks and minimum gate.

    Each sampled surface height is replaced by its object-plane height when
    the triangle-vertex gap is outside [-0.5, 0.5]. The original then rejects
    the candidate only when the smallest of its three signed gaps exceeds
    0.1016. Height values are supplied by the recovered plane-query helpers;
    this function does not perform scene lookup or collision response.
    """
    if len(vertices) != 3 or any(len(vertex) != 3 for vertex in vertices):
        raise ValueError('three XYZ triangle vertices are required')
    if len(surface_heights) != 3 or len(object_heights) != 3:
        raise ValueError('three sampled and three object-plane heights are required')

    selected = []
    gaps = []
    for index, vertex in enumerate(vertices):
        y = f32(vertex[1])
        height = f32(surface_heights[index])
        gap = f32(y - height)
        if gap < -0.5 or gap > 0.5:
            height = f32(object_heights[index])
            gap = f32(y - height)
        selected.append(height)
        gaps.append(gap)

    minimum = gaps[0]
    for gap in gaps[1:]:
        if gap < minimum:
            minimum = gap
    return TerrainCandidateHeightResult(tuple(selected), tuple(gaps), minimum,
                                        minimum <= f32(0.1016))


def sample_triangle_candidate_heights(world, vertices, query_seed,
                                      object_plane_normal, object_plane_point):
    """Compose track lookup, quad-plane sampling and the candidate height gate.

    The world and each mutable 0x44-byte seed are bounded caller-supplied
    observations. Row-only lookup results have no plane normal in the recovered
    0x42dc50 adapter, so they are rejected as unsupported instead of assigning
    an inferred normal.
    """
    if not isinstance(world, TrackSurfaceWorld):
        raise TypeError('a bounded TrackSurfaceWorld is required')
    if len(query_seed) < 0x44:
        raise ValueError('a 0x44-byte terrain query seed is required')
    if len(object_plane_normal) != 3 or len(object_plane_point) != 3:
        raise ValueError('the object plane requires a normal and reference point')

    object_heights = tuple(plane_height(object_plane_normal, object_plane_point,
                                        vertex) for vertex in vertices)
    sampled_heights = []
    records = []
    normals = []
    for vertex in vertices:
        record = bytearray(query_seed)
        found = track_surface_lookup(world, vertex, record)
        records.append(bytes(record))
        if not found:
            sampled_heights.append(object_heights[len(sampled_heights)])
            normals.append(tuple(f32(value) for value in object_plane_normal))
            continue

        mode = int.from_bytes(record[0x0c:0x10], 'little')
        path_rows = None
        if mode == 0:
            index = int.from_bytes(record[0:4], 'little')
            if not 0 <= index < world.path_count:
                raise ValueError('row-mode query references an unavailable path')
            address = world.paths_address + index * 0x54
            path_rows = {index: world.memory.read(address, 0x54)}
        reference, normal = plane_from_query_record(
            record, read_memory=world.memory.read, path_rows=path_rows)
        if normal is None:
            raise ValueError('row-mode query has no recovered candidate-plane normal')
        sampled_heights.append(plane_height(normal, reference, vertex))
        normals.append(tuple(f32(value) for value in normal))

    candidate = triangle_candidate_height_gate(vertices, sampled_heights,
                                               object_heights)
    return TerrainCandidateSamplingResult(candidate, tuple(records), tuple(normals))


def terrain_contact_velocity_gate(vertices, normals, position, linear_velocity,
                                  angular_turn_velocity, center_of_mass_local,
                                  body_to_world, minimum_gap):
    """Recover the per-vertex motion predictor and 3-point contact gate.

    The original predicts each signed gap after 1/32 second, with the source
    bias 0.3065625 and inclusive final gap limit represented by a strict
    ``< 0.1016`` test. The caller requires all three vertices before producing
    a terrain response.
    """
    if (len(vertices) != 3 or len(normals) != 3 or
            any(len(vector) != 3 for vector in (position, linear_velocity,
                                                angular_turn_velocity,
                                                center_of_mass_local)) or
            len(body_to_world) != 9):
        raise ValueError('contact predictor requires three points, normals and body vectors')

    points = tuple(tuple(f32(value) for value in vertex) for vertex in vertices)
    ns = tuple(tuple(f32(value) for value in normal) for normal in normals)
    position = tuple(f32(value) for value in position)
    linear = tuple(f32(value) for value in linear_velocity)
    turns = tuple(f32(value) for value in angular_turn_velocity)
    com = tuple(f32(value) for value in center_of_mass_local)
    matrix = tuple(f32(value) for value in body_to_world)

    # Match the caller's z, y, x accumulation order while rotating its local
    # center-of-mass offset into the same frame as candidate points.
    center_world = (
        f32((com[2] * matrix[6] + com[1] * matrix[3]) + com[0] * matrix[0]),
        f32((com[2] * matrix[7] + com[1] * matrix[4]) + com[0] * matrix[1]),
        f32((com[2] * matrix[8] + com[1] * matrix[5]) + com[0] * matrix[2]))
    omega = tuple(f32(value * 6.2831855) for value in turns)
    dots = []
    predicted = []
    accepted = []
    minimum_gap = f32(minimum_gap)
    for index, (point, normal) in enumerate(zip(points, ns)):
        offset = tuple(f32(point[i] - position[i]) for i in range(3))
        lever = tuple(f32(offset[i] - center_world[i]) for i in range(3))
        spin = (f32(omega[1] * lever[2] - omega[2] * lever[1]),
                f32(omega[2] * lever[0] - omega[0] * lever[2]),
                f32(omega[0] * lever[1] - omega[1] * lever[0]))
        point_velocity = tuple(f32(spin[i] + linear[i]) for i in range(3))
        projection = ((float(point_velocity[0]) * normal[0] +
                       float(point_velocity[1]) * normal[1]) +
                      float(point_velocity[2]) * normal[2])
        projected_gap = (projection - 0.3065625) * 0.03125 + minimum_gap
        dots.append(projection)
        predicted.append(projected_gap)
        if projected_gap < 0.1016:
            accepted.append(index)
    selected = tuple(accepted)
    return TerrainContactVelocityResult(tuple(dots), tuple(predicted), selected,
                                        len(selected) == 3)


def terrain_impact_response(linear_velocity, angular_turn_velocity,
                            gravity_scale, normal, threshold, sliding):
    """Translate the supplied-body response helper called by 0x45a320.

    Mirrors `0x457550`'s positive-normal-load gate, friction-work bound,
    velocity changes, status and recorded tangential impulse. The caller owns
    shape, time-step and contact-selection decisions.
    """
    if (len(linear_velocity) != 3 or len(angular_turn_velocity) != 3 or
            len(normal) != 3):
        raise ValueError('terrain response requires three-component vectors')
    velocity = tuple(f32(value) for value in linear_velocity)
    angular = tuple(f32(value) for value in angular_turn_velocity)
    n = tuple(f32(value) for value in normal)
    gravity = f32(gravity_scale)
    threshold = f32(threshold)
    sliding = f32(sliding)
    load = f32(f32(n[1] * gravity) * 9.81)
    zero = (0., 0., 0.)
    if not 0. < load:
        return TerrainImpactResult(velocity, angular, 0, zero, False)

    first = (f32(velocity[1] * n[2] - velocity[2] * n[1]),
             f32(velocity[2] * n[0] - velocity[0] * n[2]),
             f32(velocity[0] * n[1] - velocity[1] * n[0]))
    tangent = (f32(first[1] * n[2] - first[2] * n[1]),
               f32(first[2] * n[0] - first[0] * n[2]),
               f32(first[0] * n[1] - first[1] * n[0]))
    squared = f32((tangent[2] * tangent[2] + tangent[1] * tangent[1]) +
                  tangent[0] * tangent[0])
    length = 0.
    if squared != 0.:
        length = f32(math.sqrt(squared))
        inverse = f32(1. / length)
        tangent = tuple(f32(value * inverse) for value in tangent)

    angular_projection = ((float(angular[0]) * n[0] +
                           float(angular[1]) * n[1]) +
                          float(angular[2]) * n[2])
    angular_turn = f32(angular_projection * 6.2831855)
    bound = f32((abs(f32(angular_turn * 16.)) + abs(f32(length * 16.))) * gravity)
    if bound == 0.:
        return TerrainImpactResult(velocity, angular, 0, zero, False)

    if float(threshold) * load < bound:
        status = 2
        response_scale = f32(f32(sliding * load) / bound)
    else:
        status = 1
        response_scale = 1.

    speed_step = f32(length * response_scale)
    new_velocity = tuple(f32(float(velocity[i]) +
                             float(tangent[i]) * speed_step) for i in range(3))
    angular_factor = float(response_scale) * angular_turn * -0.15915494
    new_angular = tuple(f32(float(angular[i]) + float(n[i]) * angular_factor)
                        for i in range(3))
    recorded = tuple(f32(value * bound) for value in tangent)
    return TerrainImpactResult(new_velocity, new_angular, status, recorded, True)
