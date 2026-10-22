"""Packed world-contact sample decoding used by 0x45d1f0."""
from dataclasses import dataclass
import math
import struct

from client.tire_response import f32


_FIXED_16_SCALE = f32(1.5258789e-5)


@dataclass(frozen=True)
class CollisionWorldSample:
    position: tuple[float, float, float]
    vertical_value: float
    radius: float
    kind: int


def decode_collision_world_sample(record):
    """Decode one 0x14-byte packed sample, matching the pure 0x42db70 path."""
    if len(record) < 0x14:
        raise ValueError('world collision sample must span 0x14 bytes')
    kind = record[0x13] & 3
    value = struct.unpack_from('<h', record, 0x0c)[0]
    radius = {
        0: 3.,
        1: 12.,
        2: 2.,
        3: 1.,
    }[kind]
    if kind == 1:
        value >>= 1
    elif kind == 2:
        value = ((value << 1) & 0xffff)
        value = value - 0x10000 if value & 0x8000 else value
    position = tuple(f32(struct.unpack_from('<i', record, offset)[0] *
                          _FIXED_16_SCALE)
                     for offset in (0, 4, 8))
    vertical = f32((value << 8) * _FIXED_16_SCALE)
    return CollisionWorldSample(position, vertical, f32(radius), kind)


def world_sample_overlaps_body(body, sample):
    """Translate the radius and oriented horizontal prefilter in 0x45d1f0."""
    if len(body) < 0x354:
        raise ValueError('collision body image must cover the world-sample fields')
    if not isinstance(sample, CollisionWorldSample):
        raise ValueError('a decoded world collision sample is required')

    x = f32(sample.position[0] - struct.unpack_from('<f', body, 8)[0])
    z = f32(sample.position[2] - struct.unpack_from('<f', body, 0x10)[0])
    horizontal_squared = f32(f32(x * x) + f32(z * z))
    horizontal_distance = f32(math.sqrt(horizontal_squared))
    body_radius = struct.unpack_from('<f', body, 0xD8)[0]
    if not horizontal_distance < f32(sample.vertical_value + body_radius):
        return False
    if not struct.unpack_from('<f', body, 0x350)[0] < sample.radius:
        return False

    matrix = struct.unpack_from('<9f', body, 0x9C)
    extent_x, extent_y, extent_z = struct.unpack_from('<3f', body, 0xCC)
    projections = tuple(f32(f32(f32(z * matrix[z_index]) + 0.0) +
                             f32(x * matrix[x_index]))
                       for z_index, x_index in ((7, 1), (6, 0), (8, 2)))
    for projection, extent in zip(projections, (extent_y, extent_x, extent_z)):
        if not abs(f32(projection)) < f32(sample.vertical_value + extent):
            return False
    return True
