"""Recovered 0x53e030 wheel speed projection; force/slip producers are external."""
from dataclasses import dataclass
import math

from client.tire_response import f32


@dataclass(frozen=True)
class WheelSpeedInput:
    angle: float
    contact: bool
    spin_value: float
    spin_scale: float


@dataclass(frozen=True)
class WheelSpeedState:
    wheels: tuple[WheelSpeedInput, ...]  # Native consecutive record order, slots 0..3.
    lateral_velocity: float
    longitudinal_velocity: float
    yaw_rate_turns: float
    front_offset: float
    rear_offset: float
    front_track: float
    rear_track: float


def project_wheel_speeds(state: WheelSpeedState):
    """Return four stored float32 speeds; airborne wheels use spin_value*scale.

    The original half-angle input is passed to turn-based sine/cosine helpers.
    The meaning/normalization of the wheel angle itself remains unresolved.
    """
    if len(state.wheels) != 4:
        raise ValueError('four native-order wheel observations required')
    lateral, longitudinal, yaw, front, rear, ft, rt = map(f32,
        (state.lateral_velocity, state.longitudinal_velocity, state.yaw_rate_turns,
         state.front_offset, state.rear_offset, state.front_track, state.rear_track))
    if min(ft, rt) <= 0:
        raise ValueError('positive axle tracks required')
    wheels = tuple((f32(w.angle), w.contact, f32(w.spin_value), f32(w.spin_scale))
                   for w in state.wheels)
    yaw = yaw * f32(6.2831855)
    half_yaw = f32(yaw * 0.5)
    front_yaw, rear_yaw = f32(yaw * front), f32(yaw * rear)
    front_delta, rear_delta = f32(half_yaw * ft), f32(half_yaw * rt)
    result = []
    for index, (angle, contact, spin, scale) in enumerate(wheels):
        local_lateral = f32(lateral + front_yaw) if index < 2 else f32(lateral - rear_yaw)
        delta = front_delta if index < 2 else rear_delta
        local_longitudinal = f32(longitudinal + (delta if index in (0, 3) else -delta))
        if not contact:
            result.append(f32(scale * spin))
            continue
        half_angle = f32(angle * 0.5)
        radians = half_angle * f32(6.2831855)
        sine_part = f32(math.sin(radians) * local_lateral)
        result.append(f32(math.cos(radians) * local_longitudinal + sine_part))
    return tuple(result)
