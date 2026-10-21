"""Track-frame setup and finalization from original routine 0x51e460."""
import math
import struct

from .matrix_math import (dot_3_f32, transpose_3x3_words,
                          float_to_word, word_to_float)
from .tire_response import f32
from .track_surface_lookup import TrackSurfaceWorld, track_surface_lookup
from .track_plane import float32_ieee, surface_height
from .geometry_transform import transform_vertices
from .world_object_environment import EnvironmentCallbacks, environment_step


RECORD_SIZE = 0x4F8
QUERY_OFFSET = 0x370


def _normalize(vector):
    x, y, z = (f32(value) for value in vector)
    squared = z * z + y * y + x * x
    if squared == 0.0:
        return x, y, z
    inverse = 1.0 / math.sqrt(squared)
    return f32(x * inverse), f32(y * inverse), f32(z * inverse)


def _transpose(matrix):
    words = tuple(float_to_word(value) for value in matrix)
    return tuple(word_to_float(value) for value in transpose_3x3_words(words))


def _write_orientation(record, flags, local_x):
    first = tuple(struct.unpack_from('<3f', record, 0x31c))
    second = tuple(struct.unpack_from('<3f', record, 0x328))
    third = tuple(struct.unpack_from('<3f', record, 0x334))
    if flags & 0x10:
        matrix = tuple(struct.unpack_from('<9f', record, 0x78))
    elif not (flags & 0x2) and not (flags & 0x1):
        matrix = first + second + third
    elif (flags & 0x2) and not (flags & 0x1):
        matrix = (f32(-first[0]), f32(-first[1]), f32(-first[2]),
                  *second, f32(-third[0]), f32(-third[1]), f32(-third[2]))
    elif local_x < 0.0:
        matrix = (f32(-third[0]), f32(-third[1]), f32(-third[2]),
                  *second, *first)
    else:
        matrix = (*third, *second,
                  f32(-first[0]), f32(-first[1]), f32(-first[2]))
    struct.pack_into('<9f', record, 0x78, *matrix)
    struct.pack_into('<9f', record, 0x9c, *_transpose(matrix))


def prepare_contact_frame(record, track_rows, track_index, query_position, flags):
    """Port the 0x51e460 prefix through its matrix setup, before child 0x51e940.

    ``flags`` is the raw dword passed in the routine's float-typed fourth
    parameter. This covers the observed bit tests and signed comparison.
    """
    if not isinstance(record, bytearray) or len(record) < RECORD_SIZE:
        raise ValueError('a mutable 0x4f8-byte world-object record is required')
    if type(track_index) is not int or not 0 <= track_index < len(track_rows):
        raise ValueError('track index must select a supplied path row')
    if type(flags) is not int or not 0 <= flags <= 0xffffffff:
        raise ValueError('contact mode flags must be a raw uint32 value')
    if len(query_position) != 3:
        raise ValueError('contact position must have three components')
    row = tuple(f32(value) for value in track_rows[track_index])
    if len(row) < 12:
        raise ValueError('track row must provide its origin and three axes')
    position = tuple(f32(value) for value in query_position)

    struct.pack_into('<8I', record, QUERY_OFFSET,
                     track_index, track_index >> 3, 0, 0, 0, 0, 0, 0)
    struct.pack_into('<I', record, 0x368, track_index)
    first = _normalize(row[9:12])
    second = _normalize(row[3:6])
    third = _normalize(row[6:9])
    struct.pack_into('<3f', record, 0x31c, *first)
    struct.pack_into('<3f', record, 0x328, *second)
    struct.pack_into('<3f', record, 0x334, *third)

    origin = row[:3]
    if flags & 0x4:
        delta = tuple(position[i] - origin[i] for i in range(3))
        local = tuple(f32(delta[2] * basis[2] +
                          delta[1] * basis[1] +
                          delta[0] * basis[0])
                      for basis in (first, second, third))
    else:
        local = position
    local_x, local_y, local_z = local
    struct.pack_into('<f', record, 0x3b8, local_x)

    if not (flags & 0x8):
        world = tuple(f32(local_z * third[i] + local_y * second[i] +
                          local_x * first[i] + origin[i])
                      for i in range(3))
        struct.pack_into('<3f', record, 8, *world)
    record[0x358:0x364] = record[8:0x14]
    _write_orientation(record, flags, local_x)
    return record


def finish_contact_frame(record, *, world, track_index):
    """Port the post-0x51e940 clearance, type and projection finalizer.

    The environment callback must already have populated the query and the
    matrix/frame fields. Surface search uses the original 0x42e760 translation
    over the supplied bounded track memory.
    """
    if not isinstance(record, bytearray) or len(record) < RECORD_SIZE:
        raise ValueError('a mutable 0x4f8-byte world-object record is required')
    if not isinstance(world, TrackSurfaceWorld):
        raise ValueError('a bounded track-surface world is required')
    if type(track_index) is not int or not 0 <= track_index < world.path_count:
        raise ValueError('track index must select a supplied path row')

    query = bytearray(record[QUERY_OFFSET:QUERY_OFFSET + 0x44])
    query_words = struct.unpack_from('<17I', query)
    clearance = 0.0
    found_any = False
    for index in range(22):
        point_offset = 0x1e8 + index * 12
        point = tuple(struct.unpack_from('<3f', record, point_offset))
        point_query = bytearray(query)
        if not track_surface_lookup(world, point, point_query):
            continue
        reference_pointer = struct.unpack_from('<I', point_query, 16)[0]
        if reference_pointer == 0:
            continue
        surface_point = tuple(world.memory.real(reference_pointer + axis * 4)
                              for axis in range(3))
        normal = tuple(struct.unpack_from('<3f', point_query, 44))
        height = surface_height(normal, surface_point, point)
        delta = float32_ieee(point[1] - height)
        if not found_any or delta < clearance:
            clearance = delta
            found_any = True

    struct.pack_into('<f', record, 0x350, 0.0)
    owner_y = struct.unpack_from('<f', record, 0x0c)[0]
    struct.pack_into('<f', record, 0x0c,
                     float32_ieee(owner_y - clearance))

    surface = query_words[3]
    surface_type = world.memory.byte(surface + 4) if surface else 0
    struct.pack_into('<II', record, 0x400, surface_type, surface_type & 0x1f)

    matrix = tuple(struct.unpack_from('<9f', record, 0x78))
    basis = tuple(struct.unpack_from('<3f', record, 0x328))
    projections = tuple(dot_3_f32(matrix[row * 3:row * 3 + 3], basis)
                        for row in range(3))
    struct.pack_into('<3f', record, 0xc0, *projections)

    points = tuple(struct.unpack_from('<66f', record, 0xe0))
    owner_position = tuple(struct.unpack_from('<3f', record, 8))
    transformed = transform_vertices(points, matrix, owner_position)
    struct.pack_into('<66f', record, 0x1e8, *transformed)
    return record


def apply_contact_frame(record, *, track_rows, track_index, query_position,
                        flags, environment_callbacks, environment_enabled):
    """Run the translated 0x51e460 setup, environment child and finalizer."""
    if not isinstance(environment_callbacks, EnvironmentCallbacks):
        raise ValueError('explicit environment callbacks are required')
    prepare_contact_frame(record, track_rows, track_index, query_position, flags)
    environment_step(record, callbacks=environment_callbacks,
                     environment_enabled=environment_enabled)
    struct.pack_into('<f', record, 0x34c,
                     f32(track_rows[track_index][1]))
    return finish_contact_frame(record, world=environment_callbacks.world,
                                track_index=track_index)
