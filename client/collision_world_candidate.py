"""Packed world-contact sample decoding used by 0x45d1f0."""
from dataclasses import dataclass
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
