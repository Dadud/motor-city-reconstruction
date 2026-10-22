"""Portable composition of the native per-world-object initializer 0x426d50.

The game owns the collision world and contact backend, so those two boundaries
are explicit callbacks. Everything around them follows the observed object
layout and recovered child routines.
"""
from __future__ import annotations

import struct

from .body_constructor import construct_body
from .matrix_math import rotation_x_turns, transpose_3x3_words
from .tire_response import f32


RECORD_SIZE = 0x4F8
DESCRIPTOR = 0x418
DESCRIPTOR_SIZE = 0xE0


def _u32(image, offset):
    return struct.unpack_from('<I', image, offset)[0]


def _f32(image, offset):
    return struct.unpack_from('<f', image, offset)[0]


def _put_f32(image, offset, value):
    struct.pack_into('<f', image, offset, f32(value))


def _clamp_min(value, minimum):
    # The x87 code selects the constant for unordered inputs as well.
    value = f32(value)
    return value if minimum < value else f32(minimum)


def _clamp(value, minimum, maximum):
    value = f32(value)
    if not (minimum <= value):
        return f32(minimum)
    if maximum < value:
        return f32(maximum)
    return value


def _transform_optional_vertices(vertices, matrix):
    """Apply the inline x87 point transform and round only at its stores."""
    output = []
    for index in range(0, 66, 3):
        x, y, z = vertices[index:index + 3]
        output.extend((f32((z * matrix[6] + y * matrix[3]) + x * matrix[0]),
                       f32((z * matrix[7] + y * matrix[4]) + x * matrix[1]),
                       f32((z * matrix[8] + y * matrix[5]) + x * matrix[2])))
    return tuple(output)


def _label(image):
    raw = bytes(image[0x4A0:0x4F8]).split(b'\0', 1)[0]
    return raw.decode('latin-1')


def _enum_shape(value):
    return value if 1 <= value <= 4 else 0


def _enum_material(value):
    # The native switch has no default assignment; its zero-initialized local
    # remains zero for out-of-range descriptor values.
    return {0: 0, 1: 3, 2: 1, 3: 4, 4: 2, 5: 5, 6: 6}.get(value, 0)


def _fallback_class(material):
    return {0: 0x11, 1: 0x14, 2: 0x0F, 3: 0x0F,
            4: 0x13, 5: 0x12, 6: 0x10}.get(material, 0x11)


def initialize_world_body(record, *, collision_classes, query_surface,
                          setup_contact, geometry_dispatch, half_turn_matrix=None,
                          initial_query_image=None):
    """Initialize one 0x4f8 world object from its embedded 0xe0 descriptor.

    ``collision_classes`` maps exact descriptor labels (for example the
    observed ``GARBAGECAN`` label) to native class IDs. ``query_surface`` gets
    the object, normalized descriptor and initialized 0x44-byte query record,
    then returns that record after the selected world's lookup.
    ``setup_contact`` receives the
    object, query result, descriptor, and native 0x18 argument.
    ``geometry_dispatch`` models the selected callback reached by the
    0x6f1320 state wrapper. When the descriptor requests the optional transform,
    ``half_turn_matrix(0.5)`` can override the recovered 3x3 child result for
    instrumentation; the source translation is used when it is omitted.
    These inputs preserve the parent routine's real dependencies instead of
    fabricating a track, material table, or render backend.
    """
    if not isinstance(record, bytearray) or len(record) != RECORD_SIZE:
        raise ValueError('mutable 0x4f8-byte world-object image required')
    if not isinstance(collision_classes, dict):
        raise TypeError('collision class lookup must be an explicit mapping')
    if not all(callable(callback) for callback in
               (query_surface, setup_contact, geometry_dispatch)):
        raise TypeError('surface, contact and geometry child boundaries are required')
    descriptor = bytes(record[DESCRIPTOR:DESCRIPTOR + DESCRIPTOR_SIZE])

    # 0x426d50 first clears the trailing helper storage and its class fields.
    record[0x4C8:0x4EC] = bytes(0x24)
    struct.pack_into('<II', record, 0x4C0, 0, 0)

    label = _label(record)
    class_id = collision_classes.get(label)
    struct.pack_into('<I', record, 0x4C4,
                     int(class_id) if class_id is not None else 0)
    for index in range(9):
        struct.pack_into('<I', record, 0x4C8 + index * 4,
                         _u32(descriptor, 0x54 + index * 4))
    struct.pack_into('<I', record, 0x4C0, _u32(descriptor, 0x50))

    # These stores normalize descriptor inputs in place before construction.
    mass = _clamp_min(_f32(descriptor, 0x0C), 25.0)
    _put_f32(record, DESCRIPTOR + 0x0C, mass)
    _put_f32(record, DESCRIPTOR + 0x10,
             _clamp_min(_f32(descriptor, 0x10), 0.0))

    shape_code = struct.unpack_from('<H', descriptor, 0x48)[0]
    shape = _enum_shape(shape_code)
    material_code = struct.unpack_from('<H', descriptor, 0x4A)[0]
    material = _enum_material(material_code)
    mapped_class = collision_classes.get(label)
    if mapped_class is None:
        struct.pack_into('<I', record, 0x4C4, _fallback_class(material))

    # Position, source basis and model extents feed the base constructor.
    position = struct.unpack_from('<3f', descriptor, 0)
    struct.pack_into('<3f', record, 0x08, *position)
    struct.pack_into('<I', record, 0x50, _u32(descriptor, 0x0C))
    rotation_words = struct.unpack_from('<9I', descriptor, 0x14)
    struct.pack_into('<9I', record, 0x78, *rotation_words)
    struct.pack_into('<9I', record, 0x9C, *transpose_3x3_words(rotation_words))
    extents = tuple(_clamp_min(_f32(descriptor, offset), 0.05)
                    for offset in (0x38, 0x3C, 0x40))
    struct.pack_into('<3f', record, 0xCC, *extents)

    # 0x51f440 owns the base 0x418-byte body image; the embedded descriptor
    # begins immediately after that region and therefore remains intact.
    initial_owner = bytes(record[0x08:0x418]) + bytes(0x2000 - (0x418 - 0x08))
    built = construct_body(initial_owner, 0xFFFFFFFE,
                           mass, extents, shape, material)
    record[:0x08] = built[:0x08]
    record[0x08:0x418] = built[0x08:0x418]

    # 0x42d8d0 initializes the 0x44-byte query record from descriptor +0x44.
    if initial_query_image is None:
        query = bytearray(0x44)
    else:
        if len(initial_query_image) != 0x44:
            raise ValueError('initial query image must contain exactly 0x44 bytes')
        query = bytearray(initial_query_image)
    query_id = _u32(descriptor, 0x44)
    struct.pack_into('<ii', query, 0, query_id,
                     ((query_id >> 3) | (0xE0000000 if query_id & 0x80000000 else 0)))
    query = query_surface(record, bytes(record[DESCRIPTOR:DESCRIPTOR + DESCRIPTOR_SIZE]),
                          query)
    if not isinstance(query, (bytes, bytearray)) or len(query) < 0x44:
        raise ValueError('surface query must return its complete 0x44-byte record')
    query = bytearray(query[:0x44])
    setup_contact(record, struct.unpack_from('<I', query, 0)[0],
                  bytes(record[DESCRIPTOR:DESCRIPTOR + DESCRIPTOR_SIZE]), 0x18)

    # Preserve the descriptor pose and mirror the query result into the owner.
    struct.pack_into('<3f', record, 0x08, *position)
    struct.pack_into('<9I', record, 0x78, *rotation_words)
    struct.pack_into('<9I', record, 0x9C, *transpose_3x3_words(rotation_words))
    record[0x370:0x3B4] = query
    record[4] = 0
    record[6] = 0
    struct.pack_into('<I', record, 0x6C, _u32(record, DESCRIPTOR + 0x10))

    geometry_dispatch(record, 0x16, 0xE0, 0x78, 0x08, 0x1E8, 0x0C)

    if _u32(descriptor, 0x7C) != 0:
        if half_turn_matrix is not None and not callable(half_turn_matrix):
            raise TypeError('half-turn matrix child must be callable')
        matrix = tuple(half_turn_matrix(0.5) if half_turn_matrix is not None
                       else rotation_x_turns(0.5))
        if len(matrix) != 9:
            raise ValueError('half-turn matrix child must return nine floats')
        vertices = struct.unpack_from('<66f', record, 0xE0)
        transformed = _transform_optional_vertices(vertices, matrix)
        struct.pack_into('<66f', record, 0xE0, *transformed)
        geometry_dispatch(record, 0x16, 0xE0, 0x78, 0x08, 0x1E8, 0x0C)

    struct.pack_into('<f', record, 0x60,
                     _clamp(_f32(descriptor, 0x78), -0.75, 0.75) * _f32(record, 0xD0))
    struct.pack_into('<f', record, 0x68,
                     _clamp(_f32(descriptor, 0x84), 0.0, 1.0))
    scale = _clamp_min(_f32(descriptor, 0x80), 0.0)
    _put_f32(record, 0x308, _f32(record, 0x308) * scale)
    return record
