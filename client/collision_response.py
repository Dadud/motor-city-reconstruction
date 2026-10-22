"""Recovered collision response helper; collision discovery is a separate stage."""
from dataclasses import dataclass
import math
import struct
from client.tire_response import f32


@dataclass(frozen=True)
class TangentialResponse:
    status: int
    vector: tuple[float, float, float]


def _ieee_f32(value):
    try:
        return struct.unpack('<f', struct.pack('<f', value))[0]
    except (OverflowError, struct.error):
        return math.copysign(float('inf'), value)


def tangential_response(relative_vector, normal, threshold_coefficient,
                        sliding_coefficient, *, allow_nonfinite=False):
    """Reproduce complete original helper 0x458390 for finite inputs.

    Coefficients retain neutral names until their producers are recovered.
    The normal is consumed as supplied; the original helper does not normalize it.
    """
    if len(relative_vector) != 3 or len(normal) != 3:
        raise ValueError('collision vectors require three components')
    rounded = _ieee_f32 if allow_nonfinite else f32
    vector = tuple(map(rounded, relative_vector))
    normal = tuple(map(rounded, normal))
    threshold, sliding = map(rounded, (threshold_coefficient, sliding_coefficient))
    approach_extended = -((vector[0]*normal[0] + vector[1]*normal[1]) +
                          vector[2]*normal[2])
    approach = rounded(approach_extended)
    if approach_extended <= 0:
        return TangentialResponse(0, (0.0, 0.0, 0.0))
    projection = tuple(rounded(approach*n) for n in normal)
    remainder = tuple(rounded(v-p) for v, p in zip(vector, projection))
    length_squared = remainder[0]**2 + (remainder[1]**2+remainder[2]**2)
    length_extended = math.sqrt(length_squared)
    length = rounded(length_extended)
    if length_squared == 0:
        return TangentialResponse(0, remainder)
    inverse_length = 1.0/length_extended
    direction = tuple(-rounded(v*inverse_length) for v in remainder)
    if length <= 0:
        return TangentialResponse(0, direction)
    if threshold*approach < length:
        scale = rounded(sliding*approach)
        return TangentialResponse(2, tuple(rounded(v*scale) for v in direction))
    return TangentialResponse(1, tuple(rounded(v*length) for v in direction))
