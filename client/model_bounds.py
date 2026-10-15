"""Original 0x4c3e50 translated/mirrored part bounds, before model union.

Callers must establish part selection, scaling and attachment transforms first.
These bounds alone do not certify complete assembled collision dimensions.
"""
from dataclasses import dataclass
import math
from client.tire_response import f32


@dataclass(frozen=True)
class PartBounds:
    minimum: tuple
    maximum: tuple


def transformed_part_bounds(part,*,mirrored=False):
    """Return None for an empty part; retain native float32 translation stores."""
    if type(mirrored) is not bool:raise ValueError('boolean mirror flag required')
    if len(part.origin)!=3 or len(part.vertices)>1_000_000:raise ValueError('bounded 3D part geometry required')
    origin=tuple(map(f32,part.origin))
    if not all(math.isfinite(v) for v in origin):raise ValueError('finite part origin required')
    low=high=None
    for point in part.vertices:
        if len(point)!=3 or not all(math.isfinite(v) for v in point):raise ValueError('finite 3D vertices required')
        x,y,z=map(f32,point)
        position=tuple(f32(v+o) for v,o in zip((-x if mirrored else x,y,z),origin))
        if low is None:low=high=position
        else:
            # The original replaces ties with the latest candidate, including -0.
            low=tuple(b if b<=a else a for a,b in zip(low,position))
            high=tuple(b if b>=a else a for a,b in zip(high,position))
    return None if low is None else PartBounds(low,high)
