"""Environment/contact sampling stage from original callback 0x51e940.

The game supplies spatial lookup, collision correction and plane sampling as
separate routines. They remain explicit callbacks until those bodies are
translated; the record orchestration and its derived metrics live here.
"""
from dataclasses import dataclass
import math
import struct

from .matrix_math import dot_3_f32
from .tire_response import f32
from .geometry_transform import transform_vertices
from .collision_impulse import plane_height
from .track_plane import surface_height
from .surface_selector import select_surface
from .track_frame import track_frame
from .environment_correction import correct_surface_collision
from .track_surface_lookup import TrackSurfaceWorld, track_surface_lookup


RECORD_SIZE = 0x4F8
SPATIAL_RECORD_SIZE = 0x44
CONTACT_POINT_COUNT = 22
CONTACT_POINTS_OFFSET = 0x1E8


def _f(record, offset):
    return struct.unpack_from('<f', record, offset)[0]


def _put_f(record, offset, value):
    struct.pack_into('<f', record, offset, f32(value))


@dataclass(frozen=True)
class EnvironmentCallbacks:
    """Native boundaries required by the collision/environment pass.

    ``world`` provides bounded mapped track, grid, block, path, and geometry
    memory for the translated 0x42e760 spatial query. The translated 0x43bfd0
    wrapper receives its unresolved ``adjust_contact(owner, block)`` and
    ``reset_vehicle_state(owner)`` children plus ``vertical_step``.
    """
    world: TrackSurfaceWorld
    adjust_contact: object
    reset_vehicle_state: object
    vertical_step: float


def environment_step(record, *, callbacks, environment_enabled):
    """Port the owned orchestration and record writes of 0x51e940.

    Spatial lookup and plane computation are explicit native dependencies.
    The caller provides exactly 17 dwords at +0x370 as the current query
    record. The collision correction callback is used only on the observed
    failed-lookup/alternate-mode branch.
    """
    if not isinstance(record, bytearray) or len(record) < RECORD_SIZE:
        raise ValueError('a mutable 0x4f8-byte world-object record is required')
    if not isinstance(callbacks, EnvironmentCallbacks):
        raise ValueError('explicit environment callbacks are required')
    if not isinstance(callbacks.world, TrackSurfaceWorld):
        raise ValueError('a bounded track-surface world is required')
    if not all(callable(fn) for fn in (callbacks.adjust_contact,
                                       callbacks.reset_vehicle_state)):
        raise ValueError('both original correction child callbacks are required')
    if type(environment_enabled) is not bool:
        raise ValueError('environment mode must be an observed boolean')
    if record[4] == 0:
        return record

    query = bytearray(record[0x370:0x370 + SPATIAL_RECORD_SIZE])
    position_offset = 8
    position = tuple(_f(record, position_offset + axis * 4) for axis in range(3))
    result = track_surface_lookup(callbacks.world, position, query)
    if result == 0:
        position = tuple(_f(record, 0x358 + axis * 4) for axis in range(3))
        for axis, value in enumerate(position):
            _put_f(record, 8 + axis * 4, value)
        if record[6] == 0:
            record_query = bytearray(record[0x370:0x370 + SPATIAL_RECORD_SIZE])
            result = track_surface_lookup(callbacks.world, position, record_query)
            record[0x370:0x370 + SPATIAL_RECORD_SIZE] = record_query
            query = record_query
        else:
            correct_surface_collision(
                record, struct.unpack_from('<I', query, 0)[0],
                vertical_step=callbacks.vertical_step,
                adjust_contact=callbacks.adjust_contact,
                reset_vehicle_state=callbacks.reset_vehicle_state)
            position = tuple(_f(record, 8 + axis * 4) for axis in range(3))
            query = bytearray(record[0x370:0x370 + SPATIAL_RECORD_SIZE])
    else:
        for axis in range(17):
            record[0x370 + axis * 4:0x374 + axis * 4] = query[axis * 4:axis * 4 + 4]
        position = tuple(_f(record, 8 + axis * 4) for axis in range(3))
        for axis, value in enumerate(position):
            _put_f(record, 0x358 + axis * 4, value)

    # 0x42df00 derives a track reference point and nine-float frame.
    use_track_row = struct.unpack_from('<I', query, 12)[0] == 0 or \
        struct.unpack_from('<I', query, 8)[0] != 0
    track_rows = tuple(
        tuple(callbacks.world.memory.real(callbacks.world.paths_address + index * 0x54 + axis * 4)
              for axis in range(21))
        for index in range(callbacks.world.path_count))
    if use_track_row:
        reference = None
    else:
        reference_address = struct.unpack_from('<I', query, 16)[0]
        reference = tuple(callbacks.world.memory.real(reference_address + axis * 4)
                           for axis in range(3))
    reference_point, frame = track_frame(query, track_rows, reference)
    if len(reference_point) != 3 or len(frame) != 9:
        raise ValueError('surface frame must return a point and nine matrix values')
    for axis, value in enumerate(frame):
        _put_f(record, 0x31C + axis * 4, value)
    for axis, value in enumerate(reference_point):
        _put_f(record, 0x340 + axis * 4, value)

    surface_pointer = struct.unpack_from('<I', query, 12)[0]
    surface_flags = callbacks.world.memory.byte(surface_pointer + 4) if surface_pointer else None
    result = int(select_surface(position, struct.unpack_from('<I', query, 0)[0],
                                query, track_rows, surface_flags))
    struct.pack_into('<i', record, 0x36C, result)
    record[0x354:0x358] = struct.pack('<I', int(environment_enabled and result == 0))
    surface_type = callbacks.world.memory.byte(surface_pointer + 4) if surface_pointer else 0
    struct.pack_into('<II', record, 0x400, surface_type, surface_type & 0x1F)

    basis = tuple(_f(record, 0x328 + i * 4) for i in range(3))
    for axis, offset in enumerate((0x78, 0x84, 0x90)):
        vector = tuple(_f(record, offset + i * 4) for i in range(3))
        _put_f(record, 0xC0 + axis * 4, dot_3_f32(vector, basis))

    matrix = tuple(_f(record, 0x78 + i * 4) for i in range(9))
    points = tuple(_f(record, 0xE0 + i * 4) for i in range(66))
    transformed = transform_vertices(points, matrix, position)
    for i, value in enumerate(transformed):
        _put_f(record, CONTACT_POINTS_OFFSET + i * 4, value)

    track_index = struct.unpack_from('<I', query, 0)[0]
    track_row = track_rows[track_index]
    origin = tuple(f32(track_row[i]) for i in range(3))
    # The original stores the first float at track-row +0x24 three times
    # before calling the dot helper; the duplicate loads are confirmed in
    # 0x51e940 assembly at 0x51eb63..0x51eb78.
    repeated_normal = f32(track_row[9])
    plane_normal = (repeated_normal, repeated_normal, repeated_normal)
    displacement = tuple(position[i] - origin[i] for i in range(3))
    _put_f(record, 0x3B8, dot_3_f32(displacement, plane_normal))
    x_speed, y_speed, z_speed = (_f(record, 0x14), _f(record, 0x18), _f(record, 0x1C))
    _put_f(record, 0x3B4, math.sqrt(x_speed*x_speed + z_speed*z_speed))
    normal = tuple(_f(record, 0x328 + i * 4) for i in range(3))
    plane_point = tuple(_f(record, 0x340 + i * 4) for i in range(3))
    if _f(record, 0x32C) <= 0.1:
        _put_f(record, 0x34C, -32000.0)
    else:
        _put_f(record, 0x34C, plane_height(normal, plane_point, position))

    minimum = None
    for index in range(CONTACT_POINT_COUNT):
        point = tuple(_f(record, CONTACT_POINTS_OFFSET + index * 12 + i * 4)
                      for i in range(3))
        point_query = bytearray(query)
        found = track_surface_lookup(callbacks.world, point, point_query)
        surface_address = struct.unpack_from('<I', point_query, 16)[0]
        if found and surface_address:
            surface_point = tuple(callbacks.world.memory.real(surface_address + axis * 4)
                                  for axis in range(3))
            # The copied 0x44-byte query tail begins at stack local_64 (query
            # +0x2c); 4b71a0 consumes its first three plane coefficients.
            contact_normal = tuple(_f(point_query, 44 + i * 4) for i in range(3))
            # In this caller the x87 height return remains in ST(0) through the
            # following subtraction; only the final clearance store rounds to
            # float32. Other callers that store +0x34c round the helper result
            # before their next operation and continue to use plane_height.
            distance = surface_height(contact_normal, surface_point, point)
            clearance = f32(point[1] - distance)
            if minimum is None or clearance < minimum:
                minimum = clearance
    _put_f(record, 0x350, 0.0 if minimum is None else minimum)
    return record
