"""Composition of original track lookup, plane construction and height sampling."""
import struct

from .tire_response import f32
from .track_plane import (float32_ieee, plane_from_query_record,
                          surface_height)
from .track_surface_lookup import TrackSurfaceWorld, track_surface_lookup


QUERY_SIZE = 0x44


def sample_track_surface(world, query_state, point, track_index):
    """Port the state and output behavior of original routine 0x42e010.

    ``query_state`` and ``point`` are mutable native memory images. The lookup
    retains the caller's query tail, as the original routine initializes only
    dwords 0..7 before calling 0x42e760.
    """
    if not isinstance(world, TrackSurfaceWorld):
        raise TypeError('a bounded TrackSurfaceWorld is required')
    if not isinstance(query_state, bytearray) or len(query_state) < QUERY_SIZE:
        raise ValueError('a mutable 0x44-byte surface query is required')
    if not isinstance(point, bytearray) or len(point) < 12:
        raise ValueError('a mutable three-float point is required')
    if type(track_index) is not int or not -0x80000000 <= track_index <= 0x7fffffff:
        raise ValueError('track index must fit a signed native dword')

    struct.pack_into('<i', query_state, 0, track_index)
    struct.pack_into('<i', query_state, 4, track_index >> 3)
    struct.pack_into('<6I', query_state, 8, 0, 0, 0, 0, 0, 0)
    position = struct.unpack_from('<3f', point)
    if not track_surface_lookup(world, position, query_state):
        return False

    if struct.unpack_from('<I', query_state, 12)[0] == 0:
        raise ValueError('native lookup succeeded without a surface plane normal')
    reference, normal = plane_from_query_record(
        query_state, read_memory=world.memory.read)
    if normal is None:
        raise ValueError('native lookup succeeded without a surface plane normal')
    height = surface_height(normal, reference, position)
    struct.pack_into('<f', point, 4, float32_ieee(height))
    return True
