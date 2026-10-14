"""Original 0x53d920 support-mask normal loads, isolated from contact production."""
from dataclasses import dataclass
import math
from client.tire_response import f32


@dataclass(frozen=True)
class NormalLoadInput:
    support: tuple[bool, bool, bool, bool]  # LF RF LR RR
    pitch: float
    bank: float
    mass: float
    wheelbase: float
    front_track: float
    rear_track: float
    height_parameter: float
    front_lever: float
    rear_lever: float
    speed: float
    curvature_scale: float
    vertical_correction: float
    wheel_scales: tuple[float, float, float, float]


def normal_load(state: NormalLoadInput):
    if len(state.support) != 4 or any(type(x) is not bool for x in state.support):
        raise ValueError('four boolean support observations required')
    if len(state.wheel_scales) != 4:
        raise ValueError('four wheel scale observations required')
    scales = tuple(map(f32, state.wheel_scales))
    pitch, bank, mass, wheelbase, ft, rt, height, front, rear, speed, curvature, vertical = map(f32,
        (state.pitch, state.bank, state.mass, state.wheelbase, state.front_track,
         state.rear_track, state.height_parameter, state.front_lever, state.rear_lever,
         state.speed, state.curvature_scale, state.vertical_correction))
    if mass <= 0 or min(wheelbase, ft, rt, curvature) <= 0:
        raise ValueError('positive mass, dimensions and curvature scale required')
    support = state.support
    if sum(support) < 2 or abs(pitch) > 0.25:
        return (0.0,) * 4
    height = f32(height * f32(0.9090909))
    factor = f32(mass * 0.5 / wheelbase)
    front_load, rear_load = f32(factor * rear), f32(factor * front)
    turn = f32(6.2831855)
    cosine = f32(math.cos(pitch * turn))
    sine = math.sin(pitch * turn)
    front_pitch = f32(((cosine - 1.0) * rear - sine * height) * factor)
    rear_pitch = f32(((cosine - 1.0) * front + sine * height) * factor)
    bank_angle = f32(bank * f32(3.1415927))
    front_bank = f32((front_load + front_load) * 0.5 * (height / ft) * bank_angle)
    rear_bank = f32((rear_load + rear_load) * 0.5 * (height / rt) * bank_angle)
    loads = [front_load, front_load, rear_load, rear_load]
    if sum(support) == 2 and not any(support[:2]):
        loads = [0.0, 0.0, f32(rear_bank * 0.5 + front_load + rear_load),
                 f32(-rear_bank * 0.5 + front_load + rear_load)]
    elif sum(support) == 2 and not any(support[2:]):
        loads = [f32(front_bank * 0.5 + rear_load + front_load),
                 f32(-front_bank * 0.5 + rear_load + front_load), 0.0, 0.0]
    else:
        for start, correction, banking in ((0, front_pitch, front_bank), (2, rear_pitch, rear_bank)):
            if all(support[start:start+2]):
                loads[start] = f32(banking * 0.5 + correction + loads[start])
                loads[start+1] = f32(-banking * 0.5 + correction + loads[start+1])
            else:
                active = start if support[start] else start+1
                other = start+1 if support[start] else start
                loads[active] = f32(correction + correction + loads[other] + loads[active])
                loads[other] = 0.0
    banking = min(6.0, abs(f32(math.sin(bank * turn) * speed * speed / curvature)))
    return tuple(max(0.0, f32(((scale - vertical) + banking) * load))
                 for scale, load in zip(scales, loads))
