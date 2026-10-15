"""Recovered axle vertical contributions and wheel-load adjustment (0x536250)."""
from dataclasses import dataclass
from client.tire_response import f32


@dataclass(frozen=True)
class BodyVerticalLoadState:
    speed: float
    longitudinal_speed: float
    front_parameter: float
    rear_parameter: float
    front_speed_parameter: float
    rear_speed_parameter: float
    front_adjustment: float
    rear_adjustment: float
    front_quality: float
    rear_quality: float
    wheel_loads: tuple[float, ...]


@dataclass(frozen=True)
class BodyVerticalLoadOutput:
    front_vertical: float
    rear_vertical: float
    total_vertical: float
    wheel_loads: tuple[float, ...]


def adjust_body_vertical_load(s: BodyVerticalLoadState) -> BodyVerticalLoadOutput:
    if len(s.wheel_loads) != 4:
        raise ValueError('four consecutive wheel loads required')
    speed, velocity, front, rear, fs, rs, fa, ra, fq, rq = map(f32, (
        s.speed, s.longitudinal_speed, s.front_parameter, s.rear_parameter,
        s.front_speed_parameter, s.rear_speed_parameter, s.front_adjustment,
        s.rear_adjustment, s.front_quality, s.rear_quality))
    loads = list(map(f32, s.wheel_loads))
    if speed >= f32(8.9406):
        front = f32(front + fs)
        rear = f32(rear + rs)
    if fa != 0:
        front = f32(front * (1-fa if front >= 0 else 1+fa))
    if ra != 0:
        rear = f32(rear * (1-ra if rear >= 0 else 1+ra))
    scale = abs(velocity)*f32(4.905)
    fv, rv = f32(scale*front), f32(scale*rear)
    for i in range(4):
        contribution = fv if i < 2 else rv
        quality = fq if i < 2 else rq
        loads[i] = max(0.0, f32(loads[i] + (1-quality)*contribution))
    return BodyVerticalLoadOutput(fv, rv, f32(fv+rv), tuple(loads))
