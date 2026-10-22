"""Candidate-record broadphase used by the dynamic pair pass at 0x45cf70."""
from dataclasses import dataclass
import struct


def _f32(value):
    return struct.unpack('<f', struct.pack('<f', value))[0]


def _get_f32(data, offset):
    return struct.unpack_from('<f', data, offset)[0]


@dataclass(frozen=True)
class DynamicPairCandidate:
    eligible: bool
    center: tuple
    radius: float
    within_radius: bool


def dynamic_pair_candidate(owner, record):
    """Translate the record gates and transformed-center radius test.

    ``owner`` is the mutable body image. ``record`` is one 0x78-byte entry
    from the game's dynamic candidate table. This covers only the early pair
    broadphase; record setup and the pair resolver remain separate stages.
    """
    if len(owner) < 0xdc or len(record) < 0x78:
        raise ValueError('owner and candidate images must cover their source fields')
    eligible = (_get_f32(record, 0x74) != 0.0 and
                _get_f32(record, 0x30) != 0.0)
    matrix = tuple(_get_f32(record, 0x0c + 4 * i) for i in range(9))
    local = tuple(_get_f32(record, 0x4c + 4 * i) for i in range(3))
    origin = tuple(_get_f32(record, 4 * i) for i in range(3))
    center = (
        _f32(_f32(_f32(_f32(local[2] * matrix[6]) +
                       _f32(local[1] * matrix[3])) +
                   _f32(local[0] * matrix[0])) + origin[0]),
        _f32(_f32(_f32(_f32(local[2] * matrix[7]) +
                       _f32(local[1] * matrix[4])) +
                   _f32(local[0] * matrix[1])) + origin[1]),
        _f32(_f32(_f32(_f32(local[2] * matrix[8]) +
                       _f32(local[1] * matrix[5])) +
                   _f32(local[0] * matrix[2])) + origin[2]))
    radius = _f32(_get_f32(owner, 0xd8) + _get_f32(record, 0x48))
    delta = tuple(_f32(_get_f32(owner, offset) - center[axis])
                  for axis, offset in enumerate((8, 0x0c, 0x10)))
    distance_squared = _f32(_f32(_f32(delta[0] * delta[0]) +
                                 _f32(delta[1] * delta[1])) +
                             _f32(delta[2] * delta[2]))
    within = eligible and distance_squared <= _f32(radius * radius)
    return DynamicPairCandidate(eligible, center, radius, within)
