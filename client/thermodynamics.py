"""Portable cylinder-state stages; full cycle integration remains unfinished."""
from dataclasses import dataclass
import math

from .dyno_solver import CylinderGeometry, _f32


@dataclass(frozen=True)
class InitialCylinderState:
    pressure: float
    temperature: float
    crank_radius: float
    rod_ratio: float
    piston_area: float
    mass_term: float
    reference_mass_term: float


def initial_cylinder_state(geometry, stroke_inches, start_angle, pressure=44.1):
    """Initialize the cycle state recovered at 0x479e4d–0x479f35.

    Pressure is supplied by the caller: the original first RPM starts at 44.1
    and later cycles retain/carry state. Mass-term units remain unverified.
    This function does not select or evolve that inter-cycle pressure.
    """
    if not isinstance(geometry, CylinderGeometry):
        raise ValueError('expected recovered cylinder geometry')
    values = (stroke_inches, start_angle, pressure, geometry.bore_squared,
              geometry.rod_length, geometry.clearance_volume)
    if not all(math.isfinite(v) for v in values):
        raise ValueError('non-finite cylinder initialization input')
    stroke, angle, stored_pressure, bore_squared, rod, clearance = map(_f32, values)
    if not (0 < stroke <= 5.1 and rod > 0 and bore_squared > 0 and
            clearance > 0 and stored_pressure > 0):
        raise ValueError('invalid cylinder initialization geometry/state')
    radians = angle*_f32(.017453292)
    sine = _f32(math.sin(radians))
    one_minus_cosine = _f32(1-math.cos(radians))
    crank_radius = _f32(stroke*.5)
    projection = _f32((stroke*.5/rod)*sine)
    ratio = _f32((rod+rod)/stroke)
    area = _f32(bore_squared*_f32(.7853982))
    root_argument = 1-projection*projection
    if root_argument < 0:
        raise ValueError('invalid connecting-rod geometry')
    volume = (((1-math.sqrt(root_argument))*ratio+one_minus_cosine)*
              area*crank_radius+clearance)
    return InitialCylinderState(stored_pressure, 2000, crank_radius, ratio, area,
                                _f32(volume*stored_pressure*_f32(7.8104307e-7)),
                                _f32(volume*_f32(4.357242e-5)))
