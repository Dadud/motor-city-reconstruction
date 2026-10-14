"""Recovered 26-knot wheel response consumers, not a complete tire model.

Tables are supplied by the caller; no original table data is distributed.
Native offsets +4/+8 are native angle values, +0xd4 is load, +0xf8 a multiplier.
The physical meaning of the second angle and table units remains under study.
"""
from dataclasses import dataclass
import math
import struct


def f32(value):
    try:
        result = struct.unpack('<f', struct.pack('<f', value))[0]
    except (OverflowError, struct.error) as exc:
        raise ValueError('value exceeds finite float32 range') from exc
    if not math.isfinite(result):
        raise ValueError('finite float32 values required')
    return result


@dataclass(frozen=True)
class WheelCurveInput:
    slip_angle: float
    secondary_angle: float
    normal_load: float
    surface_multiplier: float


def wheel_response(table, angle_coefficient, wheel: WheelCurveInput, *, secondary=False,
                   alternate_load=False):
    """0x53f630 (primary) / 0x53f830 (secondary), rounded storage boundaries.

    Returns float32 as stored by the original caller. alternate_load reproduces
    the observed global switch only on the primary path, not a mod setting.
    Negative load is rejected by this authored API; NaN behavior is unsupported.
    """
    if len(table) != 26:
        raise ValueError('wheel response requires exactly 26 knots')
    knots = tuple(f32(x) for x in table)
    coefficient = f32(angle_coefficient)
    slip, angle, load, surface = (f32(x) for x in
        (wheel.slip_angle, wheel.secondary_angle, wheel.normal_load,
         wheel.surface_multiplier))
    if load < 0:
        raise ValueError('nonnegative normal load required')
    degrees = f32(slip * 180.0)
    coordinate = min(abs(degrees), 25.0)
    index = math.floor(coordinate)
    curve = f32(knots[index] + (knots[min(index + 1, 25)] - knots[index]) *
                (coordinate - index))
    scaled_load = f32(load * f32(0.00025))
    if secondary:
        scale = f32(max(1.0, min(5.0, f32(scaled_load * f32(2.83) - 2.0)))) if scaled_load > 1 else max(0.0, scaled_load)
    elif alternate_load:
        bounded = max(0.0, min(3.5, scaled_load))
        polynomial = f32(bounded * bounded * f32(-0.1941) + bounded * f32(1.2262))
        scale = max(0.0, min(2.0, polynomial))
    elif scaled_load > 1:
        polynomial = f32(scaled_load * scaled_load * f32(-0.1941) +
                         scaled_load * f32(1.2262) - f32(0.031))
        scale = max(1.0, min(2.5, polynomial))
    else:
        scale = max(0.0, min(1.0, scaled_load))
    angle_term = angle * 180.0 * coefficient * load
    if secondary:
        angle_term *= f32(0.15)
    response = (angle_term + scale * curve) * surface
    if (secondary and degrees < 0) or (not secondary and degrees > 0):
        response = -response
    return f32(response)
