"""Early collision-candidate checks from original routine 0x43bd30."""
import struct

from .tire_response import f32
from .track_topology import (bounded_path_index, collision_search_bit,
                             collision_search_slot, track_index_is_rejected)
from .track_surface_lookup import TrackSurfaceWorld
from .track_surface_sample import sample_track_surface


ROW_SIZE = 0x54
WORLD_OBJECT_SIZE = 0xE7C
TRAFFIC_ROW_SIZE = 0x4F8


def _word(data, offset):
    return struct.unpack_from('<I', data, offset)[0]


def _real(data, offset):
    return struct.unpack_from('<f', data, offset)[0]


def _neighbor_indices(index, count, *, clamp):
    return (index,
            bounded_path_index(index, -1, count, clamp=clamp),
            bounded_path_index(index, 1, count, clamp=clamp))


def collision_candidate_point(rows, track_index, longitudinal, lateral):
    """Build the 3D query point from track origin and its two local axes."""
    row = rows[track_index]
    longitudinal = f32(longitudinal)
    lateral = f32(lateral)
    point = []
    for axis in range(3):
        origin = _real(row, axis * 4)
        lateral_delta = f32(_real(row, (axis + 6) * 4) * lateral)
        longitudinal_delta = f32(_real(row, (axis + 9) * 4) * longitudinal)
        point.append(f32(origin + lateral_delta + longitudinal_delta))
    return tuple(point)


def sample_collision_surface(world, point, track_index):
    """Bridge 0x42e010 output into the surface fields consumed by 0x43bd30."""
    if not isinstance(world, TrackSurfaceWorld):
        raise TypeError('a bounded TrackSurfaceWorld is required')
    query = bytearray(0x44)
    sampled_point = bytearray(struct.pack('<3f', *point))
    found = sample_track_surface(world, query, sampled_point, track_index)
    if not found:
        return False, None, None
    descriptor = _word(query, 12)
    if descriptor == 0:
        raise ValueError('successful collision sample has no surface descriptor')
    surface_flags = world.memory.byte(descriptor + 4)
    normal_y = _real(query, 48)
    return True, surface_flags, normal_y


def probe_collision_candidate(owner, track_index, longitudinal, lateral, *,
                               path_rows, path_count, range_start,
                               range_end, lower_limit, upper_limit,
                               clamp_indices, surface_vcall_result,
                               sample_surface, world_objects=(),
                               traffic_rows=(), owner_address=None):
    """Port the 0x43bd30 prefilters and point construction.

    ``sample_surface`` represents the 0x42e010 lookup and returns
    ``(found, surface_flags, normal_y)``. The 0x437b20 helper returns zero in
    AL; the separate object-vtable result is supplied explicitly as
    ``surface_vcall_result``. The final 0.8 threshold applies to the stored
    vertical plane coefficient, not the sampled point height.
    """
    if not isinstance(owner, (bytes, bytearray)) or len(owner) < WORLD_OBJECT_SIZE:
        raise ValueError('world-object image must include the +0xe78 collision slot')
    if type(path_count) is not int or path_count != len(path_rows) or path_count < 1:
        raise ValueError('path count must match the nonempty row table')
    if type(track_index) is not int or not 0 <= track_index < path_count:
        raise ValueError('track index must select a supplied row')
    if not callable(sample_surface):
        raise ValueError('an explicit surface-sampling callback is required')

    row = path_rows[track_index]
    slot = collision_search_slot(_real(row, 0x38), _real(row, 0x3c), longitudinal)
    mask = _word(row, 0x4c)
    if collision_search_bit(mask, slot) == 0:
        return False
    if track_index_is_rejected(
            track_index, range_start=range_start, range_end=range_end,
            lower_limit=lower_limit, upper_limit=upper_limit):
        return False

    nearby_slots = (slot, (slot - 1) & 0xffffffff, (slot + 1) & 0xffffffff)
    for entry in world_objects:
        if (isinstance(entry, tuple) and len(entry) == 2 and
                type(entry[0]) is int):
            other_address, other = entry
        else:
            other_address, other = None, entry
        if not isinstance(other, (bytes, bytearray)) or len(other) < WORLD_OBJECT_SIZE:
            raise ValueError('world-object collision entries must include +0xe78')
        if (other is owner or (owner_address is not None and
                               other_address == owner_address) or other[4] == 0):
            continue
        other_slot = _word(other, 0xE78)
        if other_slot in nearby_slots:
            other_index = _word(other, 0x370)
            if track_index in _neighbor_indices(other_index, path_count,
                                                clamp=clamp_indices):
                return False

    for traffic in traffic_rows:
        if not isinstance(traffic, (bytes, bytearray)) or len(traffic) < TRAFFIC_ROW_SIZE:
            raise ValueError('traffic rows must be 0x4f8-byte records')
        traffic_index = _word(traffic, 0)
        if not 0 <= traffic_index < path_count:
            continue
        traffic_offset = _real(traffic, 0x48)
        traffic_row = path_rows[traffic_index]
        traffic_slot = collision_search_slot(
            _real(traffic_row, 0x38), _real(traffic_row, 0x3c), traffic_offset)
        if traffic_slot in nearby_slots:
            if track_index in _neighbor_indices(traffic_index, path_count,
                                                clamp=clamp_indices):
                return False

    point = collision_candidate_point(path_rows, track_index,
                                      longitudinal, lateral)
    found, surface_flags, normal_y = sample_surface(point, track_index)
    if not found:
        return False
    if type(surface_vcall_result) is not int or not -0x80000000 <= surface_vcall_result <= 0xffffffff:
        raise ValueError('surface virtual-call result must be a 32-bit integer')
    # FUN_00437b20 is a literal zero-return helper. The following object
    # interface call is state-dependent; native behavior applies this gate
    # only when that call also returns zero.
    if surface_vcall_result == 0:
        flags = 0 if surface_flags is None else surface_flags & 0xff
        if flags & 0x40 or (flags & 0x1f) in (0, 0x0e) or normal_y < 0.8:
            return False
    return True
