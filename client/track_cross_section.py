"""Track cross-section geometry produced by native function 0x495240."""
import math
import struct

from .matrix_math import normalized_cross3
from .tire_response import f32


_F32 = struct.Struct('<f')


def _round32(value):
    return _F32.unpack(_F32.pack(value))[0]


def build_track_cross_section(object_transform, basis, vertical_offset, origin_scale,
                              view_reference, world_origin, radius, angle_offset):
    """Return ``(three 3D points, angle)`` for the native 0x495240 routine.

    ``object_transform`` contains 14 binary32 values corresponding to object
    offsets 0x00..0x34; the routine consumes indices 5..13. ``basis`` contains
    the three consecutive world basis floats at 0x8915b8..0x8915c0;
    ``world_origin`` corresponds to globals 0x8915a8..0x8915b0.
    Angles are supported when the resulting normalized angle stays in [0, 1],
    where native wrap helper 0x4b70f0 leaves the value unchanged.
    """
    object_transform = tuple(f32(v) for v in object_transform)
    basis = tuple(f32(v) for v in basis)
    view_reference = tuple(f32(v) for v in view_reference)
    world_origin = tuple(f32(v) for v in world_origin)
    vertical_offset, origin_scale, radius, angle_offset = map(
        f32, (vertical_offset, origin_scale, radius, angle_offset))
    if len(object_transform) != 14:
        raise ValueError('track object transform requires fourteen float32 values')
    if any(len(values) != 3 for values in (basis, view_reference, world_origin)):
        raise ValueError('basis, view reference and origin each require three values')

    # The source performs these three dot products with x87 intermediates and
    # stores each component to a local float before continuing.
    direction = (
        _round32(basis[0] * object_transform[5] +
                 basis[1] * object_transform[8] +
                 basis[2] * object_transform[11]),
        0.0,
        _round32(basis[0] * object_transform[7] +
                 basis[1] * object_transform[10] +
                 basis[2] * object_transform[13]),
    )
    if direction[0] == 0.0 and direction[2] == 0.0:
        direction = (direction[0], 0.0, 1.0)
    magnitude = math.sqrt(direction[2] * direction[2] +
                          direction[0] * direction[0])
    if magnitude != 0.0:
        direction = (_round32(direction[0] / magnitude), 0.0,
                     _round32(direction[2] / magnitude))

    angle = (math.atan2(direction[0], direction[2]) *
             0.15915493667125702 + 0.5 + angle_offset)
    angle = _round32(angle)
    if not 0.0 <= angle <= 1.0:
        raise ValueError('angle offset leaves the verified native no-wrap range')

    cross = normalized_cross3(tuple(view_reference[i] - direction[i]
                                   for i in range(3)),
                             tuple(world_origin[i] - direction[i] for i in range(3)))
    scaled_direction = tuple(_round32(v * radius) for v in direction)
    origin = tuple(_round32(v * origin_scale) for v in world_origin)
    turn_scale = _round32(radius * 6.28318) * 0.0625
    scaled_cross = tuple(_round32(v * turn_scale) for v in cross)
    point0 = (scaled_direction[0],
              _round32(vertical_offset + scaled_direction[1]), scaled_direction[2])
    point1 = (_round32(origin[0] + scaled_direction[0]),
              _round32(_round32(origin[1] + scaled_direction[1]) + vertical_offset),
              _round32(origin[2] + scaled_direction[2]))
    point2 = (_round32(scaled_direction[0] + scaled_cross[0]),
              _round32(_round32(scaled_direction[1] + scaled_cross[1]) + vertical_offset),
              _round32(scaled_direction[2] + scaled_cross[2]))
    return (point0, point1, point2), angle
