"""Original acceleration-driven normal-load correction at 0x53e680.

The initial loads, acceleration transform and two axle offsets are explicit
inputs. Complete suspension/contact producers remain separate recovery work.
"""
from dataclasses import dataclass
from client.tire_response import f32


@dataclass(frozen=True)
class LoadTransferInput:
    loads: tuple[float, float, float, float]  # Original processing order: LF RF LR RR.
    attitude: float
    longitudinal_acceleration: float
    lateral_acceleration: float
    speed: float
    mass: float
    wheelbase: float
    front_track: float
    rear_track: float
    height_parameter: float
    front_offset: float
    rear_offset: float


def transfer_load(state: LoadTransferInput):
    if len(state.loads) != 4:
        raise ValueError('four original-order normal loads required')
    loads = list(map(f32, state.loads))
    attitude, longitudinal, lateral, speed, mass, wheelbase, ft, rt, height, fo, ro = map(f32,
        (state.attitude, state.longitudinal_acceleration, state.lateral_acceleration,
         state.speed, state.mass, state.wheelbase, state.front_track, state.rear_track,
         state.height_parameter, state.front_offset, state.rear_offset))
    if min(loads) < 0 or mass <= 0 or min(wheelbase, ft, rt) <= 0:
        raise ValueError('nonnegative loads and positive mass/dimensions required')
    height = f32(height * f32(0.9090909))
    if abs(attitude) > 0.25:
        return tuple(loads)
    if abs(longitudinal) > f32(0.1962):
        correction = f32(-longitudinal * (height / wheelbase) * mass * 0.5)
        loads = [max(0.0, f32(load + (correction if index < 2 else -correction)))
                 for index, load in enumerate(loads)]
    if abs(lateral) > f32(0.1962) and abs(speed) > 6.0:
        # Both corrections read the already corrected axle sums, before either
        # lateral correction is written. Clamp each individual load afterward.
        front = f32((loads[0] + loads[1]) * f32(0.101936795) *
                    (((height - fo * f32(0.8)) * lateral) / ft))
        rear = f32((loads[2] + loads[3]) * f32(0.101936795) *
                   (((height - ro * f32(0.8)) * lateral) / rt))
        loads = [max(0.0, f32(loads[0] + front)), max(0.0, f32(loads[1] - front)),
                 max(0.0, f32(loads[2] + rear)), max(0.0, f32(loads[3] - rear))]
    return tuple(loads)
