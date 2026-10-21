"""Supplied-world support geometry recovered from original routine 0x459150."""
from dataclasses import dataclass
import math
import struct
from dataclasses import replace

from .collision_pair_response import CollisionImpactBody, resolve_surface_impulse
from .geometry_transform import transform_vertices
from .tire_response import f32
from .track_surface_lookup import TrackSurfaceWorld, track_surface_lookup


@dataclass(frozen=True)
class SupportQuery:
    """One candidate point and the mutated 0x44-byte track query record."""
    index: int
    relative_point: tuple
    world_point: tuple
    record: bytes
    reference_point: tuple | None
    normal: tuple | None
    signed_distance: float | None
    eligible: bool


@dataclass(frozen=True)
class SupportGeometryResult:
    position: tuple
    relative_points: tuple
    world_points: tuple
    queries: tuple
    correction: tuple


@dataclass(frozen=True)
class SupportImpactResult:
    body: CollisionImpactBody
    support_count: int
    impacted_points: tuple


def _dot(a, b):
    return f32((a[0] * b[0] + a[1] * b[1]) + a[2] * b[2])


def _add(a, b):
    return tuple(f32(a[i] + b[i]) for i in range(3))


def _sub(a, b):
    return tuple(f32(a[i] - b[i]) for i in range(3))


def _scale(a, value):
    return tuple(f32(component * value) for component in a)


def _normalized(vector):
    squared = _dot(vector, vector)
    if squared == 0.0:
        return (0., 0., 0.)
    inverse = f32(1.0 / math.sqrt(squared))
    return tuple(f32(component * inverse) for component in vector)


def correct_support_geometry(world, position, orientation, local_points,
                             query_seeds, vertical_velocity):
    """Translate the first geometry/query/correction pass of ``0x459150``.

    The routine transforms 22 local points without translation, queries the
    track at each world point whose transformed local Y is nonpositive, and
    applies the original one-step vertical-motion and signed-plane tests. On
    penetration it translates the object and every transformed point together.
    Per-point query seeds are 0x44-byte records copied from the caller's
    ``+0x370`` table. The returned query records retain the descriptor and
    first-vertex pointers needed by :func:`resolve_support_contacts`.
    """
    if not isinstance(world, TrackSurfaceWorld):
        raise TypeError('a bounded TrackSurfaceWorld is required')
    position = tuple(f32(value) for value in position)
    orientation = tuple(f32(value) for value in orientation)
    local_points = tuple(f32(value) for value in local_points)
    seeds = tuple(bytes(value) for value in query_seeds)
    if len(position) != 3 or len(orientation) != 9:
        raise ValueError('support correction requires position and 3x3 orientation')
    if len(local_points) != 66 or len(seeds) != 22 or any(len(seed) < 0x44 for seed in seeds):
        raise ValueError('support geometry requires 22 points and 22 0x44-byte query seeds')
    velocity_y = f32(vertical_velocity)
    relative = transform_vertices(local_points, orientation, (0., 0., 0.))
    queries = []
    correction = (0., 0., 0.)
    one_step = f32(velocity_y * .03125)
    motion_allowance = f32(max(-one_step, 0.))

    for index in range(22):
        offset = index * 3
        local = tuple(relative[offset:offset + 3])
        record = bytearray(seeds[index])
        if local[1] > 0.:
            queries.append(SupportQuery(index, local, _add(position, local),
                                        bytes(record), None, None, None, False))
            continue
        point = _add(position, local)
        if not track_surface_lookup(world, point, record):
            queries.append(SupportQuery(index, local, point, bytes(record),
                                        None, None, None, False))
            continue

        normal_values = struct.unpack_from('<3f', record, 0x2c)
        normal = _normalized(normal_values)
        reference_pointer = struct.unpack_from('<I', record, 0x10)[0]
        reference = struct.unpack('<3f', world.memory.read(reference_pointer, 12))
        distance = _dot(_sub(point, reference), normal)
        eligible = (-1. <= f32(distance - one_step) and
                    distance < motion_allowance and _dot(local, normal) < 0.)
        queries.append(SupportQuery(index, local, point, bytes(record),
                                    reference, normal, distance, eligible))
        if eligible and distance < 0.:
            step_correction = _scale(normal, f32(-distance))
            position = _add(position, step_correction)
            correction = _add(correction, step_correction)

    world_points = tuple(_add(position, relative[i:i + 3])
                         for i in range(0, len(relative), 3))
    return SupportGeometryResult(position, tuple(relative), world_points,
                                 tuple(queries), correction)


def resolve_support_contacts(world, body, geometry, coefficient_table,
                             response_scale, response_mode):
    """Translate the second, per-support impulse pass of original 0x459150.

    ``coefficient_table`` supplies the original 32 pairs at 0x89c0a8/0x89c0ac
    as (threshold, sliding) values. Query record +0x0c identifies the material
    descriptor, and +0x10 identifies the first surface vertex used by the
    caller's second signed-distance test.
    """
    if not isinstance(world, TrackSurfaceWorld):
        raise TypeError('a bounded TrackSurfaceWorld is required')
    if not isinstance(body, CollisionImpactBody):
        raise TypeError('a collision impact body is required')
    if not isinstance(geometry, SupportGeometryResult) or len(geometry.queries) != 22:
        raise ValueError('22 support query results are required')
    if len(coefficient_table) != 32 or any(len(pair) != 2 for pair in coefficient_table):
        raise ValueError('the original 32-entry coefficient table is required')
    if type(response_mode) is not int:
        raise ValueError('support response mode must be an integer')
    scale = f32(response_scale)
    mode_scale = .65 if response_mode == 1 else .25 if response_mode == 2 else 1.
    motion_allowance = f32(max(-f32(body.linear_velocity[1] * .03125), 0.))
    current = replace(body, position=geometry.position)
    impacted = []

    for query in geometry.queries:
        if not query.eligible or query.normal is None:
            continue
        point = _add(geometry.position, query.relative_point)
        reference_pointer = struct.unpack_from('<I', query.record, 0x10)[0]
        reference = struct.unpack('<3f', world.memory.read(reference_pointer, 12))
        distance = _dot(_sub(point, reference), query.normal)
        if distance > motion_allowance + .001:
            continue

        descriptor = struct.unpack_from('<I', query.record, 0x0c)[0]
        material = 0 if descriptor == 0 else world.memory.byte(descriptor + 4) & 0x1f
        threshold, sliding = coefficient_table[material]
        threshold = f32(f32(threshold) * scale)
        sliding = f32(f32(sliding) * scale)
        if response_mode in (1, 2):
            threshold = f32(threshold * mode_scale)
            sliding = f32(sliding * mode_scale)

        result = resolve_surface_impulse(current, point, query.normal,
                                         threshold, sliding)
        if not result.collided:
            continue
        current = result.body
        record = bytearray(current.contact_record)
        struct.pack_into('<I', record, 0x3f8, material)
        current = replace(current, contact_record=bytes(record))
        impacted.append(query.index)

    return SupportImpactResult(current, len(impacted), tuple(impacted))
