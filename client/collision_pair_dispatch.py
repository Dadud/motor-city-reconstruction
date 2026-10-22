"""Track-candidate and sampled-plane object-pair dispatcher from 0x45c3e0.

The surface lookup is supplied as a bounded TrackSurfaceWorld. This keeps the
original candidate producer explicit while composing the recovered query,
identity/height gates, edge selector and single-body response.
"""
from dataclasses import dataclass
import math
import struct
from typing import Callable

from client.collision_edge_contact import CollisionEdgeRecord, resolve_edge_contact
from client.collision_pair_gate import PairCandidateRecord, accepts_pair_candidate
from client.collision_pair_surface import resolve_pair_surface
from client.collision_world_response import extract_world_contact_points
from client.geometry_transform import transform_vertices
from client.track_surface_lookup import (TrackSurfaceWorld,
                                         track_surface_lookup)
from client.tire_response import f32


_PAIR_COEFFICIENTS = ((1.0, .9), (.8, .7), (1.0, .9), (.95, .86),
                      (1.0, .9), (.8, .7), (.95, .86), (.95, .86))
_DT = f32(1.0 / 32.0)


@dataclass(frozen=True)
class PairSurfaceQuery:
    """The two interpretations of one 0x42e760 result record."""
    point: tuple
    gate: PairCandidateRecord
    edge: CollisionEdgeRecord
    result: int


@dataclass(frozen=True)
class PairDispatchResult:
    body_image: bytes
    sampled_points: int
    surface_queries: int
    gated_pairs: int
    edge_tests: int
    accepted_edges: int
    responses: int
    last_type_code: int | None
    event_requests: int


def _matrix_product(left, right):
    """Float-stored 3x3 product matching 0x6f2a60."""
    out = [0.0] * 9
    for row in range(3):
        for column in range(3):
            out[row * 3 + column] = f32(
                left[row * 3] * right[column] +
                left[row * 3 + 1] * right[column + 3] +
                left[row * 3 + 2] * right[column + 6])
    return tuple(out)


def _axis_rotation(axis, turns):
    angle = float(turns) * 6.2831854820251465
    sine, cosine = f32(math.sin(angle)), f32(math.cos(angle))
    if axis == 0:
        return (1., 0., 0., 0., cosine, sine, 0., -sine, cosine)
    if axis == 1:
        return (cosine, 0., -sine, 0., 1., 0., sine, 0., cosine)
    return (cosine, sine, 0., -sine, cosine, 0., 0., 0., 1.)


def swept_pose(body_image, timestep=_DT):
    """Translate 0x520110/0x4b7430: predict orientation and origin by dt."""
    image = bytes(body_image)
    if len(image) < 0x9c:
        raise ValueError('body image must cover the pose and orientation fields')
    dt = f32(timestep)
    position = struct.unpack_from('<3f', image, 8)
    linear = struct.unpack_from('<3f', image, 0x14)
    angular_turns = tuple(f32(value * dt) for value in
                          struct.unpack_from('<3f', image, 0x38))
    matrix = struct.unpack_from('<9f', image, 0x78)
    center = struct.unpack_from('<3f', image, 0x5c)
    old_center = tuple(f32((center[2] * matrix[i + 6] +
                            center[1] * matrix[i + 3] +
                            center[0] * matrix[i]) + position[i])
                       for i in range(3))
    delta = _matrix_product(
        _matrix_product(_axis_rotation(0, angular_turns[0]),
                        _axis_rotation(1, angular_turns[1])),
        _axis_rotation(2, angular_turns[2]))
    future_matrix = _matrix_product(delta, matrix)
    future_center = tuple((center[2] * future_matrix[i + 6] +
                           center[1] * future_matrix[i + 3] +
                           center[0] * future_matrix[i]) + position[i]
                          for i in range(3))
    future_position = tuple(f32((linear[i] * dt + old_center[i]) -
                                future_center[i] + position[i])
                            for i in range(3))
    return future_position, future_matrix


def _read_query(world, point, seed):
    record = bytearray(seed)
    result = track_surface_lookup(world, point, record)
    descriptor = struct.unpack_from('<I', record, 0x0c)[0]
    pointers = struct.unpack_from('<4I', record, 0x10)
    vertices = tuple(world.memory.read(pointer, 12) if pointer else bytes(12)
                     for pointer in pointers)
    vertices = tuple(struct.unpack('<3f', vertex) for vertex in vertices)
    material_flags = world.memory.byte(descriptor + 4) if descriptor else 0
    gate = PairCandidateRecord(
        struct.unpack_from('<I', record, 4)[0], material_flags,
        struct.unpack_from('<I', record, 8)[0], vertices,
        struct.unpack_from('<f', record, 0x24)[0])
    weights = world.memory.read(descriptor, 4) if descriptor else bytes(4)
    edge = CollisionEdgeRecord(descriptor, vertices, weights)
    return PairSurfaceQuery(tuple(struct.unpack_from('<3f', record, 0x20)),
                            gate, edge, result)


def _contact_type(world, path_index, point):
    if not isinstance(world, TrackSurfaceWorld):
        raise TypeError('a TrackSurfaceWorld is required for material classification')
    if type(path_index) is not int or not 0 <= path_index < world.path_count:
        raise ValueError('body query seed does not contain a valid path index')
    row = world.paths_address + path_index * 0x54
    values = struct.unpack('<6f', world.memory.read(row, 12) +
                           world.memory.read(row + 0x24, 12))
    delta = tuple(f32(point[i] - values[i]) for i in range(3))
    dot = (delta[0] * values[3] + delta[1] * values[4] +
           delta[2] * values[5])
    return world.memory.byte(row + (0x51 if dot > 0.0 else 0x50))


def _planar_distance(left, right):
    dx = f32(left[0] - right[0])
    dz = f32(left[2] - right[2])
    return math.sqrt(dx * dx + dz * dz)


def dispatch_track_pairs(body_image, world, *, contact_links=None,
                         event_callback: Callable | None = None):
    """Run the 0x45c3e0 per-vertex dispatcher using the recovered track query.

    World links default to the owner's eight entries in the supplied block
    table. The native virtual event target is not resolved here; an optional
    callback receives the updated body and contact normal when requested.
    """
    image = bytes(body_image)
    if len(image) < 0x478:
        raise ValueError('body image must cover 0x478 bytes used by the dispatcher')
    if not isinstance(world, TrackSurfaceWorld):
        raise TypeError('a TrackSurfaceWorld is required')
    if (image[0x400] & 0x80) == 0:
        return PairDispatchResult(image, 0, 0, 0, 0, 0, 0, None, 0)
    seed = image[0x370:0x370 + 0x44]
    seed_index = struct.unpack_from('<I', seed)[0]
    owner_id = struct.unpack_from('<I', image, 0x374)[0]
    if contact_links is None:
        link_address = world.blocks_address + owner_id * 0x6c4 + 0x6a4
        contact_links = struct.unpack('<8I', world.memory.read(link_address, 32))
    else:
        contact_links = tuple(contact_links)
    if len(contact_links) != 8:
        raise ValueError('the owner requires exactly eight contact links')

    points = extract_world_contact_points(image)
    position = struct.unpack_from('<3f', image, 8)
    matrix = struct.unpack_from('<9f', image, 0x78)
    future_position, future_matrix = swept_pose(image)
    current_world = transform_vertices(points.vertices, matrix, position,
                                       count=points.count)
    future_world = transform_vertices(points.vertices, future_matrix,
                                      future_position, count=points.count)
    current_image = image
    queries = gated = edge_tests = accepted_edges = responses = events = 0
    last_type = None
    seed_pointers = struct.unpack_from('<4I', seed, 0x10)
    seed_vertices = tuple(world.memory.read(pointer, 12) if pointer else bytes(12)
                          for pointer in seed_pointers)
    seed_edge = CollisionEdgeRecord(
        struct.unpack_from('<I', seed, 0x0c)[0],
        tuple(struct.unpack('<3f', value) for value in seed_vertices),
        (world.memory.read(struct.unpack_from('<I', seed, 0x0c)[0], 4)
         if struct.unpack_from('<I', seed, 0x0c)[0] else bytes(4)))

    for index in range(points.count):
        current_point = tuple(current_world[index * 3:index * 3 + 3])
        future_point = tuple(future_world[index * 3:index * 3 + 3])
        first = _read_query(world, current_point, seed)
        second = _read_query(world, future_point, seed)
        queries += 2
        if first.edge.identity != 0 and first.edge.identity == second.edge.identity:
            continue
        gated += 1
        first_allowed = accepts_pair_candidate(owner_id, contact_links, first.gate)
        if not first_allowed:
            second_allowed = accepts_pair_candidate(owner_id, contact_links,
                                                    second.gate)
            if not second_allowed:
                continue
            edge = resolve_edge_contact(future_point, first.edge, second.edge)
            edge_tests += 1
            if not edge.accepted:
                edge = resolve_edge_contact(future_point, seed_edge, second.edge)
                edge_tests += 1
            query_point = future_point
            contact = edge.point
            normal = edge.normal
            vertical = edge.vertical_value
            distance = _planar_distance(contact, query_point)
        else:
            edge = resolve_edge_contact(current_point, seed_edge, first.edge)
            edge_tests += 1
            query_point = current_point
            contact = edge.point
            normal = edge.normal
            vertical = edge.vertical_value
            distance = _planar_distance(contact, query_point)
        if not edge.accepted:
            continue
        accepted_edges += 1
        type_code = _contact_type(world, seed_index, contact)
        if type_code == 0 or type_code > 7:
            type_code = 4
        last_type = type_code
        base_threshold, base_sliding = _PAIR_COEFFICIENTS[type_code]
        multiplier = struct.unpack_from('<f', current_image, 0x318)[0]
        threshold = f32(base_threshold * multiplier)
        sliding = f32(base_sliding * multiplier)
        mode = struct.unpack_from('<I', current_image, 0x354)[0]
        if mode == 1:
            threshold, sliding = f32(threshold * .65), f32(sliding * .65)
        elif mode == 2:
            threshold, sliding = f32(threshold * .25), f32(sliding * .25)
        result = resolve_pair_surface(
            current_image, struct.unpack_from('<I', current_image, 0)[0],
            normal, contact, f32(distance + .5), threshold, sliding, vertical)
        if result.collided:
            updated = bytearray(result.body_image)
            struct.pack_into('<I', updated, 0x3f4, 3)
            struct.pack_into('<I', updated, 0x3f8, type_code)
            current_image = bytes(updated)
            responses += 1
            if current_image[6] != 0 and current_image[0x474] & 2:
                events += 1
                if event_callback is not None:
                    current_image = bytes(event_callback(current_image,
                                                         tuple(normal)))
    return PairDispatchResult(current_image, points.count, queries, gated,
                              edge_tests, accepted_edges, responses, last_type,
                              events)
