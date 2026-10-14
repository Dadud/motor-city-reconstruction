"""Original 0x53e980 attitude and torque-dependent normal-load correction."""
from dataclasses import dataclass
import math
from client.tire_response import f32


@dataclass(frozen=True)
class SuspensionLoadInput:
    loads: tuple[float, float, float, float]  # LF RF LR RR accumulator order
    support: tuple[bool, bool, bool, bool]
    attitude: float
    enabled: bool
    speed: float
    bank_angle: float
    pitch_angle: float
    mass: float
    mass_offset: float
    front_weight_parameter: float
    rear_weight_parameter: float
    front_lever: float
    rear_lever: float
    wheelbase: float
    rear_track: float
    gear_factor: float
    torque: float
    component_mode: int
    disable_torque: bool


def correct_suspension_load(state: SuspensionLoadInput):
    if len(state.loads) != 4 or len(state.support) != 4 or any(type(x) is not bool for x in state.support):
        raise ValueError('four loads and boolean support observations required')
    loads = list(map(f32, state.loads))
    attitude, speed, bank, pitch, mass, offset, fw, rw, fl, rl, wheelbase, track, gear, torque = map(f32,
        (state.attitude, state.speed, state.bank_angle, state.pitch_angle, state.mass,
         state.mass_offset, state.front_weight_parameter, state.rear_weight_parameter,
         state.front_lever, state.rear_lever, state.wheelbase, state.rear_track,
         state.gear_factor, state.torque))
    if min(loads) < 0 or min(wheelbase, track) <= 0 or mass < offset or mass <= 0 or fw+rw <= 0:
        raise ValueError('invalid normal load, mass, dimensions or weight parameters')
    if type(state.component_mode) is not int or not -0x80000000 <= state.component_mode <= 0x7fffffff:
        raise ValueError('int32 component mode required')
    if abs(attitude) > 0.25 or not state.enabled:
        return tuple(loads)
    total = f32(fw + rw)
    weight = f32((mass - offset) * f32(9.81))
    front_fraction, rear_fraction = f32(fw / total), f32(rw / total)
    turn = f32(6.2831855)
    if abs(speed) > 6:
        bank_sine = math.sin(-bank * turn)
        front_bank = f32(bank_sine * front_fraction * weight)
        rear_bank = bank_sine * rear_fraction * weight
        for i, contribution in enumerate((front_bank, -front_bank, rear_bank, -rear_bank)):
            if state.support[i]:
                loads[i] = f32(loads[i] + contribution)
        pitch_sine = math.sin(-pitch * turn)
        front_pitch = f32((front_fraction * weight * fl * 2 / wheelbase) * pitch_sine)
        rear_pitch = (rear_fraction * weight * rl * 2 / wheelbase) * pitch_sine
        for i, contribution in enumerate((front_pitch, front_pitch, -rear_pitch, -rear_pitch)):
            if state.support[i]:
                loads[i] = f32(loads[i] + contribution)
        loads = [max(0.0, load) for load in loads]
    if state.component_mode == 0 and not state.disable_torque:
        correction = f32(abs(gear * torque * rw * 0.5 / (track * total)))
        loads[2] = max(0.0, f32(loads[2] + correction))
        loads[3] = max(0.0, f32(loads[3] - correction))
    return tuple(loads)
