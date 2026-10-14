"""Observed 0x540520 wheel-force transformation; parameter producers are external."""
from dataclasses import dataclass, replace
import math
from client.tire_response import f32


@dataclass(frozen=True)
class ForceOrientationWheel:
    steering_angle: float
    phase_angle: float
    lateral_force: float
    longitudinal_force: float


def orient_wheel_forces(wheels, front_parameter, rear_parameter):
    if len(wheels)!=4:
        raise ValueError('four consecutive wheel records required')
    front,rear=map(f32,(front_parameter,rear_parameter))
    turn=f32(6.2831855)
    out=[]
    for i,w in enumerate(wheels):
        angle,phase,lateral,longitudinal=map(f32,(w.steering_angle,w.phase_angle,w.lateral_force,w.longitudinal_force))
        phase=f32(i*.25+phase)
        angle=f32(angle+math.sin(phase*turn)*(front if i<2 else rear)*f32(.044444445))
        sine=math.sin(angle*turn)
        cosine=f32(math.cos(angle*turn))
        out.append(replace(w,lateral_force=f32(lateral-sine*longitudinal),
                           longitudinal_force=f32(cosine*longitudinal-sine*lateral)))
    return tuple(out)
