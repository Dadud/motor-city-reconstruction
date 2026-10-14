"""Original 0x53e3d0 wheel resistance contribution with explicit observations.

The mode predicate is supplied; its producer and the full force tick are separate.
"""
from dataclasses import dataclass, replace
import math

from client.tire_response import f32


@dataclass(frozen=True)
class ResistanceWheel:
    slip_angle: float
    surface_id: int
    normal_load: float
    rolling_speed: float
    speed_scale: float
    contact: bool
    longitudinal_force: float


@dataclass(frozen=True)
class ResistanceResult:
    wheels: tuple[ResistanceWheel, ...]
    last_contribution: float


def rolling_resistance(wheels, speed, front_coefficient, rear_coefficient,
                       front_adjustment, rear_adjustment, body_angle, *,
                       disabled_flag=False, mode_predicate=False, alternate=False):
    """Preserves force state at gates; result is last computed, not summed force.

    speed_scale must be positive; physical units of component coefficients remain
    unresolved. body_angle uses the original turn-based cosine helper.
    """
    if len(wheels) != 4:
        raise ValueError('four wheel observations required')
    speed, front, rear, fa, ra, angle = map(f32,
        (speed, front_coefficient, rear_coefficient, front_adjustment, rear_adjustment, body_angle))
    validated = []
    for wheel in wheels:
        if type(wheel.surface_id) is not int or not 0 <= wheel.surface_id <= 0xffffffff:
            raise ValueError('uint32 surface identifier required')
        slip, load, rolling, scale, force = map(f32, (wheel.slip_angle, wheel.normal_load,
            wheel.rolling_speed, wheel.speed_scale, wheel.longitudinal_force))
        if load < 0 or scale <= 0:
            raise ValueError('nonnegative load and positive speed scale required')
        validated.append(replace(wheel, slip_angle=slip, normal_load=load,
            rolling_speed=rolling, speed_scale=scale, longitudinal_force=force))
    if abs(speed) < 2 or disabled_flag or mode_predicate:
        return ResistanceResult(tuple(validated), 0.0)
    updated = []
    last = 0.0
    cosine = math.cos(abs(angle) * f32(6.2831855))
    for index, wheel in enumerate(validated):
        if wheel.surface_id == 2:
            coefficient = f32(abs(speed) * f32(0.000096) + f32(0.012))
        elif wheel.surface_id in (3, 5):
            coefficient = f32(abs(speed) * f32(0.000072) + f32(0.013))
        else:
            coefficient = f32(abs(speed) * f32(0.000048) + f32(0.01))
        axle = f32(((fa if index < 2 else ra) + 1.0) * (front if index < 2 else rear))
        degrees = f32(abs(wheel.slip_angle * 180.0))
        amplification = max(1.0, min(8.0, f32((degrees * f32(0.0831) +
            degrees * degrees * f32(0.0988)) * 0.5 + 1.0)))
        projection = cosine * (amplification if alternate else 1.0)
        last = f32(-(projection * wheel.normal_load * f32(axle * coefficient * 0.5)))
        if wheel.rolling_speed < 0:
            last = -last
        force = wheel.longitudinal_force
        if wheel.contact and 1.0 / wheel.speed_scale < abs(wheel.rolling_speed) and wheel.normal_load != 0:
            force = f32(force + last)
        updated.append(replace(wheel, longitudinal_force=force))
    return ResistanceResult(tuple(updated), last)
