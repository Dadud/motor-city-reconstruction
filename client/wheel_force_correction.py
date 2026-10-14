"""Complete recovered 0x53e130; coefficients and control producers remain external."""
from dataclasses import dataclass, replace
import math

from client.tire_response import f32


@dataclass(frozen=True)
class ForceCorrectionWheel:
    projected_speed: float
    spin_value: float
    spin_adjustment: float
    spin_scale: float
    lateral_force: float
    longitudinal_force: float
    normal_load: float
    primary_coefficient: float
    secondary_coefficient: float
    contact: bool
    correction_enabled: bool


def correct_wheel_forces(wheels, service_control, other_control, parking_control,
                         direction_mode, override_control):
    """Return adjusted spin state in native consecutive record order.

    service_control (+a90), other_control (+a94), parking_control (+a6b),
    direction_mode (+a69), override_control (+a88) are observed caller state.
    Their UI/input mapping is not reconstructed by this function.
    """
    if len(wheels) != 4 or type(direction_mode) is not int or not 0 <= direction_mode <= 255:
        raise ValueError('four wheels and byte direction mode required')
    service, other = map(f32, (service_control, other_control))
    result = []
    for index, wheel in enumerate(wheels):
        speed, spin, adjustment, scale, lateral, longitudinal, load, primary, secondary = map(f32,
            (wheel.projected_speed, wheel.spin_value, wheel.spin_adjustment, wheel.spin_scale,
             wheel.lateral_force, wheel.longitudinal_force, wheel.normal_load,
             wheel.primary_coefficient, wheel.secondary_coefficient))
        if scale <= 0 or load < 0 or min(primary, secondary) < 0:
            raise ValueError('positive spin scale and nonnegative load/coefficients required')
        if type(wheel.contact) is not bool or type(wheel.correction_enabled) is not bool:
            raise ValueError('boolean contact and correction observations required')
        if load != 0 and wheel.contact:
            mismatch = f32(-((spin-speed/scale)*32 + adjustment))
            stop_adjustment = f32(-(spin*32 + adjustment))
            magnitude = f32(math.sqrt(lateral*lateral + longitudinal*longitudinal))
            capacity = f32(primary*load)
            secondary_capacity = f32(secondary*load)
            residual = f32(capacity-abs(longitudinal))
            lower = f32(secondary_capacity*f32(.15))
            limited = max(lower, min(capacity, residual))
            if magnitude > capacity:
                adjustment = f32(adjustment + max(0, f32(secondary_capacity-abs(longitudinal)))*mismatch/magnitude)
            elif ((service > 0 or (index >= 2 and parking_control)) and longitudinal < 0
                  or other > 0 and longitudinal > 0):
                if capacity == 0:
                    raise ValueError('nonzero primary capacity required at correction division')
                adjustment = f32(adjustment + limited*mismatch/capacity)
            else:
                adjustment = f32(adjustment+mismatch)
            if wheel.correction_enabled:
                if direction_mode >= 2 and not override_control and adjustment < stop_adjustment:
                    adjustment = stop_adjustment
                elif direction_mode == 0 and adjustment > stop_adjustment:
                    adjustment = stop_adjustment
        elif longitudinal == 0:
            spin = f32(spin*f32(.999375))
        result.append(replace(wheel, projected_speed=speed, spin_value=spin,
            spin_adjustment=adjustment, spin_scale=scale, lateral_force=lateral,
            longitudinal_force=longitudinal, normal_load=load, primary_coefficient=primary,
            secondary_coefficient=secondary))
    return tuple(result)
