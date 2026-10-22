"""Evaluate the fixed-point animation records attached to FRD objects."""
from dataclasses import dataclass, replace
import math
import struct


@dataclass(frozen=True)
class TrackObjectPose:
    sample_index: int
    fraction: float
    translation: tuple[float, float, float]
    rotation: tuple[float, ...]


def apply_track_object_pose(part, pose):
    """Apply the native object pose to local mesh vertices and normals.

    The recovered renderer reads the 3x3 matrix by columns and adds the
    sampled translation to positions. Baking the transform keeps the shared
    preview mesh path and its lighting shader consistent.
    """
    m = pose.rotation

    def rotate(vector):
        x, y, z = vector
        return (x*m[0] + y*m[3] + z*m[6],
                x*m[1] + y*m[4] + z*m[7],
                x*m[2] + y*m[5] + z*m[8])
    vertices = tuple(tuple(value + pose.translation[axis]
                           for axis, value in enumerate(rotate(vertex)))
                     for vertex in part.vertices)
    normals = tuple(rotate(normal) for normal in part.normals)
    return replace(part, origin=(0.0, 0.0, 0.0), vertices=vertices,
                   normals=normals)


def _f32(value):
    return struct.unpack('<f', struct.pack('<f', value))[0]


def evaluate_track_object_animation(animation, tick, *, mode=1):
    """Translate the sampled transform interpolation in native 0x407940.

    Mode 1 loops across the sample sequence as used by renderer dispatch
    0x58cc10. Mode 2 returns ``None`` once the final interval is reached.
    Each 20-byte sample contains three signed 16.16 translations followed by
    four signed 16-bit quaternion components.
    """
    if type(tick) is not int or tick < 0:
        raise ValueError('animation tick must be a nonnegative integer')
    if mode not in (1, 2):
        raise ValueError('animation mode must be 1 or 2')
    if len(animation) < 8:
        raise ValueError('track object animation header is truncated')
    frame_count, period = struct.unpack_from('<HH', animation, 4)
    if frame_count < 2:
        raise ValueError('track object animation needs at least two samples')
    if len(animation) < 8 + frame_count * 20:
        raise ValueError('track object animation samples are truncated')
    if period == 0 or period > 400:
        period = 6
    interval = tick // period
    if mode == 2 and interval >= frame_count - 1:
        return None
    sample_index = interval % (frame_count - 1)
    remainder = tick % period
    fraction = remainder / period
    fraction = _f32(fraction)
    unit = _f32(1.5259022e-5)
    next_weight = fraction * unit
    current_weight = (1.0 - fraction) * unit
    base = 8 + sample_index * 20
    next_base = base + 20
    current_translation = struct.unpack_from('<3i', animation, base)
    next_translation = struct.unpack_from('<3i', animation, next_base)
    translation = tuple(_f32(current * current_weight + nxt * next_weight)
                        for current, nxt in zip(current_translation,
                                                next_translation))
    # The native calculation first stores its fractional weights as float32,
    # then scales quaternion words by 4/65535.
    next_weight = fraction * 4.0 * unit
    current_weight = (1.0 - fraction) * 4.0 * unit
    current_quaternion = struct.unpack_from('<4h', animation, base + 12)
    next_quaternion = struct.unpack_from('<4h', animation, next_base + 12)
    quaternion = tuple(_f32(current * current_weight + nxt * next_weight)
                       for current, nxt in zip(current_quaternion,
                                               next_quaternion))
    x, y, z, w = quaternion
    xx, yy, zz = 2.0 * x, 2.0 * y, 2.0 * z
    rotation = tuple(_f32(value) for value in (
        1.0 - yy * y - zz * z, xx * y + zz * w, zz * x - yy * w,
        xx * y - zz * w, 1.0 - xx * x - zz * z, zz * y + xx * w,
        zz * x + yy * w, zz * y - xx * w, 1.0 - xx * x - yy * y,
    ))
    if not all(math.isfinite(value) for value in translation + rotation):
        raise ValueError('track object animation produced a non-finite pose')
    return TrackObjectPose(sample_index, fraction, translation, rotation)
