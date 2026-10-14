"""Authored reconstruction of original driving RPM helper 0x546e70.

Inputs describe recovered fields, not a complete gearbox or engine tick.
Integer conversion uses round-to-nearest/even after original float stores.
"""
from dataclasses import dataclass, replace
import math
from client.tire_response import f32


@dataclass(frozen=True)
class DrivingEngineRPM:
    idle_rpm: int
    configured_max_rpm: int
    throttle: float
    normalized_rpm: float
    target_rpm: int
    enabled: bool
    inertia_factor: float
    acceleration_input: float
    angular_speed: float
    rpm: int
    limiter_rpm: int
    gear_index: int
    gear_speed_factor: float
    longitudinal_speed: float
    acceleration_output: float = 0.0


def update_driving_engine_rpm(state, minimum_rpm):
    """One complete helper call; caller's minimum is separate from idle RPM."""
    if type(state.enabled) is not bool:
        raise ValueError('enabled must be bool')
    for value in (state.idle_rpm, state.configured_max_rpm, state.target_rpm,
                  state.rpm, state.limiter_rpm, state.gear_index, minimum_rpm):
        if type(value) is not int or not -2**31 < value < 2**31:
            raise ValueError('RPM and gear fields must be bounded signed integers')
    throttle, normalized, inertia, acceleration, omega, factor, speed = map(f32, (
        state.throttle, state.normalized_rpm, state.inertia_factor,
        state.acceleration_input, state.angular_speed,
        state.gear_speed_factor, state.longitudinal_speed))
    if not -10 <= normalized <= 10:
        raise ValueError('normalized RPM exceeds supported comparison range')
    rads = f32(.10471976)
    rpm_scale = f32(9.549296)
    target = state.idle_rpm + round(f32(throttle * f32(1.1) *
                    (state.configured_max_rpm-state.idle_rpm)))
    target = min(max(target, state.idle_rpm), state.configured_max_rpm)
    target = state.target_rpm + round(f32((target-state.target_rpm) *
                                        math.exp(-normalized) * .0625))
    raw_acceleration = f32(inertia*acceleration) if state.enabled else 0.0
    output = f32((1-normalized)*raw_acceleration)
    if raw_acceleration < 0:
        output = max(output, f32(normalized*f32(-200)))
        delta = min(f32(output*.03125),
                    f32(-(state.rpm-target)*rads*inertia*.03125))
        omega = f32(omega+delta)
    elif state.rpm < target:
        candidate = round(f32(((1-normalized)*raw_acceleration*.03125+omega)*rpm_scale))
        omega = f32(min(candidate, target)*rads)
    else:
        if state.gear_index != 1:
            target = max(abs(round(f32(factor*speed))), target)
        omega = f32(omega-(state.rpm-target)*rads*.03125)
    if state.enabled:
        rpm = max(min(round(f32(omega*rpm_scale)), state.limiter_rpm), minimum_rpm)
        omega = f32(rpm*rads)
    else:
        rpm, omega = 0, 0.0
    return replace(state, target_rpm=target, rpm=rpm, angular_speed=omega,
                   acceleration_output=output)
