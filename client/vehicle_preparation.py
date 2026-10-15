"""Recovered vehicle orientation preparation and surface support disturbance.

Supplied owner/configuration observations remain required. These routines do
not synthesize controller input, collision contacts, or original surface data.
"""
from dataclasses import dataclass, replace
import math
from client.tire_response import f32

IDENTITY = (1., 0., 0., 0., 1., 0., 0., 0., 1.)
TAU = 6.2831854820251465
INV_TAU = .15915493667125702


@dataclass(frozen=True)
class PreparationState:
    local_vertical_acceleration: float = 0
    front_observation: float = 0
    rear_observation: float = 0
    front_factor: float = 0
    rear_factor: float = 0
    support_count: int = 0
    pitch_extent: float = 0
    roll_extent: float = 0
    pitch_limit: float = .1
    roll_limit: float = .1
    orientation_scale: float = 1
    pitch_reference: float = 0
    roll_reference: float = 0
    minimum_pitch: float = .1
    maximum_pitch: float = .1
    maximum_roll: float = .1
    pitch_offset: float = 0
    pitch: float = 0
    roll: float = 0
    extent: float = 0
    source_vector: tuple = (0., 0., 0.)
    source_matrix: tuple = IDENTITY
    motion_matrix: tuple = IDENTITY
    damping: float = 0
    pitch_target: float = 0
    roll_target: float = 0
    angle_delta: tuple = (0., 0., 0.)
    auxiliary: tuple = (0.,) * 6
    to_world: tuple = IDENTITY
    to_local: tuple = IDENTITY


def _clamp(x, low, high):
    return max(low, min(high, x))


def _matrix_product(a, b):
    # The original helper chooses differing addition orders for five cells.
    orders = ((1, 2, 0), (2, 1, 0), (2, 1, 0), (2, 1, 0),
              (0, 1, 2), (2, 1, 0), (2, 1, 0), (2, 1, 0), (2, 0, 1))
    return tuple(f32(sum(a[(i//3)*3+k]*b[k*3+i%3] for k in orders[i])) for i in range(9))


def prepare_vehicle(state: PreparationState):
    """Complete numeric 0x54ebe0, including its original trigonometric helpers."""
    numeric = {k: f32(v) for k, v in vars(state).items() if isinstance(v, (float, int)) and k != 'support_count'}
    s = replace(state, **numeric)
    if type(s.support_count) is not int or not 0 <= s.support_count <= 4:
        raise ValueError('support count must be an integer in [0, 4]')
    if min(s.minimum_pitch, s.maximum_pitch, s.maximum_roll, s.pitch_limit, s.roll_limit) < 0:
        raise ValueError('nonnegative limits required')
    if len(s.source_vector) != 3 or len(s.source_matrix) != 9 or len(s.motion_matrix) != 9:
        raise ValueError('three-vector and nine-element matrix required')
    vector = tuple(map(f32, s.source_vector)); matrix = tuple(map(f32, s.source_matrix))
    motion = tuple(map(f32,s.motion_matrix))
    if len(s.auxiliary)!=6 or len(s.angle_delta)!=3 or len(s.to_world)!=9 or len(s.to_local)!=9:
        raise ValueError('invalid retained output lengths')
    s=replace(s,source_vector=vector,source_matrix=matrix,motion_matrix=motion,
        auxiliary=tuple(map(f32,s.auxiliary)),angle_delta=tuple(map(f32,s.angle_delta)),
        to_world=tuple(map(f32,s.to_world)),to_local=tuple(map(f32,s.to_local)))
    if (s.pitch_reference,s.orientation_scale,s.roll_reference) != (matrix[1],matrix[4],matrix[7]):
        raise ValueError('orientation observations must agree with the supplied source matrix')
    damping = 1.
    if s.local_vertical_acceleration > 0:
        damping = f32(1 - (1 - s.rear_observation*.5)*s.rear_factor)
    elif s.local_vertical_acceleration < 0:
        damping = f32(1 - (1 - s.front_observation*.5)*s.front_factor)
    damping = _clamp(damping, 0., 1.)
    pitch, roll, extent = s.pitch, s.roll, s.extent
    pitch_target, roll_target = s.pitch_target, s.roll_target
    auxiliary = s.auxiliary
    if s.support_count < 2:
        max_extent = max(s.pitch_limit, s.roll_limit)
        scale = _clamp(s.orientation_scale, 0., 1.)
        transformed = tuple(f32((vector[0]*motion[i] + vector[1]*motion[i+3]) + vector[2]*motion[i+6]) for i in range(3))
        pitch_response = f32(math.atan2(s.pitch_reference, abs(s.orientation_scale))*INV_TAU*scale)
        roll_response = f32(math.atan2(s.roll_reference, abs(s.orientation_scale))*INV_TAU*scale)
        pitch_target = f32(roll_response - math.atan2(transformed[2], transformed[1])*INV_TAU + s.pitch_offset)
        roll_target = f32(pitch_response - math.atan2(transformed[0], transformed[1])*INV_TAU)
        desired_pitch = _clamp(roll_response, -s.minimum_pitch, s.maximum_pitch)
        desired_roll = _clamp(pitch_response, -s.maximum_roll, s.maximum_roll)
        p_extent = abs(f32(math.sin(s.roll*TAU)*s.pitch_extent))
        r_extent = abs(f32(math.sin(s.pitch*TAU)*s.roll_extent))
        desired_extent = max(max(p_extent, r_extent), f32(scale*max_extent*f32(.66)))
        delta = tuple(f32((a-b)*.015625) for a,b in ((desired_pitch,s.pitch),(desired_roll,s.roll),(desired_extent,s.extent)))
        # FST at +0xc58 stores the delta but retains its extended value for
        # the pitch addition. Roll/extent instead reload stored deltas.
        pitch = _clamp(f32(s.pitch+(desired_pitch-s.pitch)*.015625), -s.minimum_pitch, s.maximum_pitch)
        roll = _clamp(f32(s.roll+delta[1]), -s.maximum_roll, s.maximum_roll)
        extent = _clamp(f32(s.extent+delta[2]), 0., max_extent)
        auxiliary = (0.,)*6
    else:
        delta = (0., 0., 0.)
    ps, pc = f32(math.sin(pitch*TAU)), f32(math.cos(pitch*TAU))
    rs, rc = f32(math.sin(roll*TAU)), f32(math.cos(roll*TAU))
    pitch_matrix = (1.,0.,0.,0.,pc,ps,0.,-ps,pc)
    roll_matrix = (rc,rs,0.,-rs,rc,0.,0.,0.,1.)
    world = _matrix_product(_matrix_product(pitch_matrix,roll_matrix),matrix)
    local = tuple(world[j*3+i] for i in range(3) for j in range(3))
    return replace(s, damping=damping, pitch=pitch, roll=roll, extent=extent,
                   pitch_target=pitch_target, roll_target=roll_target,
                   angle_delta=delta, auxiliary=auxiliary, to_world=world, to_local=local)


@dataclass(frozen=True)
class SupportWheel:
    contact: bool
    bound_parameter: float
    amplitude: float
    frequency: float
    displacement: float = 0
    correction: float = 0


@dataclass(frozen=True)
class SupportState:
    wheels: tuple
    phase: float
    local_longitudinal_speed: float
    noise: tuple


def update_support_disturbance(state: SupportState):
    """0x427da0 with required, separately supplied 256-byte lookup table."""
    if len(state.wheels)!=4 or len(state.noise)!=256 or any(type(x) is not int or not 0<=x<=255 for x in state.noise):
        raise ValueError('four wheels and a 256-byte lookup table required')
    phase, speed = f32(state.phase), f32(state.local_longitudinal_speed)
    wheels=[]
    for i,w in enumerate(state.wheels):
        if type(w.contact) is not bool:raise ValueError('boolean contact required')
        load, amp, frequency, old = map(f32,(w.bound_parameter,w.amplitude,w.frequency,w.displacement))
        if load<0:raise ValueError('nonnegative support bound required')
        if not w.contact:
            wheels.append(replace(w,displacement=0.,correction=0.));continue
        cycle = f32(phase*frequency)
        # x87 FISTP uses the declared oracle's nearest-even rounding mode.
        rounded=round(cycle)
        if not -2147483648<=rounded<=2147483647:raise ValueError('support phase outside signed conversion range')
        index = (rounded + int(i>1)) & 255
        noise = f32(state.noise[index]*.0078125-1)
        speed_factor = f32(speed*frequency*f32(6.2831855))
        disturbance = noise*amp*math.sin(cycle*TAU)
        velocity = disturbance*speed_factor
        displacement = f32(velocity*.03125+old)
        bound = min(f32(load*.25),abs(f32(disturbance)))
        wheels.append(replace(w,displacement=_clamp(displacement,-bound,bound),
                              correction=f32(f32(velocity)*speed_factor)))
    return replace(state,wheels=tuple(wheels))
