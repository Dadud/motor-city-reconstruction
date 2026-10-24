"""Track cross-section geometry produced by native function 0x495240."""
import math
import struct

from .matrix_math import atan2_turns, normalized_cross3
from .tire_response import f32


_F32 = struct.Struct('<f')


def _round32(value):
    return _F32.unpack(_F32.pack(value))[0]


def wrap_track_turn(turn):
    """Translate 0x4b70f0's in-place wrap to the native [0, 1] turn interval."""
    turn = _round32(turn)
    if turn > 1.0:
        turn = _round32(turn - math.floor(turn))
    elif turn < 0.0:
        turn = _round32(math.ceil(abs(turn)) + turn)
    return turn


def build_track_cross_section(object_transform, basis, vertical_offset, origin_scale,
                              view_reference, world_origin, radius, angle_offset):
    """Return ``(three 3D points, angle)`` for the native 0x495240 routine.

    ``object_transform`` contains 14 binary32 values corresponding to object
    offsets 0x00..0x34; the routine consumes indices 5..13. ``basis`` contains
    the three consecutive world basis floats at 0x8915b8..0x8915c0;
    ``world_origin`` corresponds to globals 0x8915a8..0x8915b0.
    Angles follow native wrap helper 0x4b70f0, including negative and
    multi-turn offsets.
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

    angle = (atan2_turns(direction[0], direction[2]) + 0.5 + angle_offset)
    angle = wrap_track_turn(_round32(angle))

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


def build_track_grid_strips(object_transform, basis, height, origin_scale,
                            view_reference, world_origin, radius,
                            angle_offset=0.0):
    """Translate native 0x495800 into two 17-point, 3D track strips."""
    object_transform = tuple(f32(v) for v in object_transform)
    if len(object_transform) != 14:
        raise ValueError('track object transform requires fourteen float32 values')
    height = f32(height)
    vertical_offset = _round32(height - object_transform[3])
    section, angle = build_track_cross_section(
        object_transform, basis, vertical_offset, origin_scale,
        view_reference, world_origin, radius, angle_offset)
    first, middle, last = section
    delta = tuple(_round32(last[i] - first[i]) for i in range(3))
    span = tuple(_round32(component * 8.0) for component in delta)
    shifted = tuple(tuple(_round32(point[i] - span[i]) for i in range(3))
                    for point in section)

    phase_product = angle * 16.0
    fractional_phase = _round32(phase_product - math.trunc(phase_product))
    correction = tuple(_round32(component * fractional_phase)
                       for component in delta)
    start = tuple(tuple(_round32(point[i] - correction[i]) for i in range(3))
                  for point in shifted)

    edge_step = tuple(start[2][i] - start[0][i] for i in range(3))
    outer_strip = [start[0], start[2]]
    for _ in range(15):
        previous = outer_strip[-1]
        outer_strip.append(tuple(_round32(previous[i] + edge_step[i])
                                 for i in range(3)))

    inner_second = tuple(_round32(start[1][i] + edge_step[i])
                         for i in range(3))
    inner_step = tuple(inner_second[i] - start[1][i] for i in range(3))
    inner_strip = [start[1], inner_second]
    for _ in range(15):
        previous = inner_strip[-1]
        inner_strip.append(tuple(_round32(previous[i] + inner_step[i])
                                 for i in range(3)))
    # Native argument order writes the centerline to param_5 and the outer
    # edge to param_6, although param_6 is emitted first in the machine code.
    return tuple(inner_strip), tuple(outer_strip), angle
