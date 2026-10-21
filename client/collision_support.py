"""Supplied-world support geometry recovered from original routine 0x459150."""
from dataclasses import dataclass
import math
import struct

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
    ``+0x370`` table. The support-impulse pass remains a separate, unresolved
    composition because the caller's post-query record pointers are not yet
    fully established.
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
