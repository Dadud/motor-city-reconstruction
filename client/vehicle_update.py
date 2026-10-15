"""Original 0x53c140 controller with explicit, mandatory child-stage execution.

This reconstructs controller-owned arithmetic and dispatch, not the missing
producers behind its child calls. The callback can mutate typed state and returns
observations for queries. No no-op executor is provided to the game runtime.
"""
from copy import deepcopy
from dataclasses import dataclass, field, fields
import math
from client.tire_response import f32

ZERO = (0., 0., 0.)
IDENTITY = (1., 0., 0., 0., 1., 0., 0., 0., 1.)


@dataclass
class UpdateWheel:
    contact: bool = False
    force: tuple = ZERO
    surface_record: int | None = None
    surface_class: int = 0
    primary_coefficient: float = 1
    secondary_coefficient: float = .8
    base_grip: float = 1
    quality: float = 1
    wear_mode: int = 0
    tire_type: int = 0
    spin_scale: float = .3
    spin: float = 0
    projected_speed: float = 0
    local_lateral: float = 0
    phase: float = 0
    primary_angle: float = 0
    clear_reference: float = 0
    clear_threshold: float = 0


@dataclass
class VehicleUpdateState:
    active: bool = True
    tilted: bool = False
    attitude: float = 1
    flags: int = 0
    linear_velocity: tuple = ZERO
    angular_velocity: tuple = ZERO
    linear_acceleration: tuple = ZERO
    angular_acceleration: tuple = ZERO
    extra_acceleration: tuple = ZERO
    local_linear: tuple = ZERO
    local_angular: tuple = ZERO
    local_acceleration: tuple = ZERO
    local_angular_acceleration: tuple = ZERO
    to_local: tuple = IDENTITY
    to_world: tuple = IDENTITY
    wheels: list = field(default_factory=lambda: [UpdateWheel() for _ in range(4)])
    speed: float = 0
    alternate_speed: float = 0
    secondary_angle: float = 0
    turning_radius_y: float = 0
    turning_radius_x: float = 0
    inverse_mass: float = .001
    mass: float = 1000
    gravity_force: float = 9800
    lateral_contribution: float = 0
    longitudinal_contribution: float = 0
    front_lever: float = 1
    rear_lever: float = 1
    front_moment: float = 0
    rear_moment: float = 0
    body_moment: float = 0
    angular_scale: float = 1
    maximum_steering: float = .1
    front_grip_gate: float = 0
    rear_grip_gate: float = 0
    environment_mode: int = 0
    fallback_surface: int = 0
    support_count: int = 0
    orientation_disabled: bool = False
    grip_boost: bool = False
    surface_coefficients: tuple = (1.,) * 32


@dataclass(frozen=True)
class UpdateCall:
    stage: str
    slot: int | None = None


@dataclass(frozen=True)
class VehicleUpdateOutput:
    state: VehicleUpdateState
    calls: tuple
    branch: str


def transform(vector, matrix):
    """Original row-vector multiply: x product, then y, then z; one store."""
    return tuple(f32((vector[0]*matrix[i] + vector[1]*matrix[3+i]) + vector[2]*matrix[6+i]) for i in range(3))


def _increment(vector, acceleration):
    return tuple(f32(v + a*.03125) for v,a in zip(vector,acceleration))


def apply_linear_update(state, enabled):
    """Original 0x540c30, mutating typed state after its supplied mode query."""
    if type(enabled) is not bool:raise ValueError('boolean vehicle gate required')
    if enabled:
        state.linear_velocity=_increment(state.linear_velocity,state.linear_acceleration)
        return
    linear=transform(state.linear_velocity,state.to_local)
    angular=transform(state.angular_velocity,state.to_local)
    state.local_linear=(0.,linear[1],0.)
    state.local_angular=(angular[0],0.,angular[2])
    state.linear_velocity=transform(state.local_linear,state.to_world)
    state.angular_velocity=transform(state.local_angular,state.to_world)
    state.linear_acceleration=ZERO;state.angular_acceleration=ZERO


def _normalize_state(s):
    if len(s.wheels)!=4 or len(s.surface_coefficients)!=32:
        raise ValueError('four wheels and 32 supplied surface coefficients required')
    for record in (s,*s.wheels):
        for item in fields(record):
            value=getattr(record,item.name)
            if item.type is float:
                setattr(record,item.name,f32(value))
        for name in ('active','tilted','contact','orientation_disabled','grip_boost'):
            if hasattr(record,name) and type(getattr(record,name)) is not bool:
                raise ValueError('boolean flags required')
    for name in ('linear_velocity','angular_velocity','linear_acceleration','angular_acceleration',
                 'extra_acceleration','local_linear','local_angular','local_acceleration',
                 'local_angular_acceleration','to_local','to_world','surface_coefficients'):
        value=getattr(s,name)
        length=9 if name in ('to_local','to_world') else 32 if name=='surface_coefficients' else 3
        if len(value)!=length:raise ValueError('invalid vector/matrix/table length')
        setattr(s,name,tuple(map(f32,value)))
    for w in s.wheels:
        if len(w.force)!=3:raise ValueError('three wheel force components required')
        w.force=tuple(map(f32,w.force))
        if w.surface_record is not None and (type(w.surface_record) is not int or not 0<=w.surface_record<=255):
            raise ValueError('surface record observation must be a byte')
    if type(s.fallback_surface) is not int or not 0<=s.fallback_surface<32:
        raise ValueError('fallback surface outside supplied table')
    if type(s.flags) is not int or not 0<=s.flags<=0xffffffff:
        raise ValueError('unsigned vehicle flags required')
    return s


def update_vehicle(state, execute):
    """Execute one controller call using mandatory supplied child-stage behavior.

    execute(UpdateCall, mutable_state) performs the named child operation. Query
    operations return observations; numeric child stages can write state. Missing
    child behavior must raise, never silently substitute a prototype.
    """
    if not callable(execute):raise ValueError('child-stage executor required')
    s=_normalize_state(deepcopy(state));calls=[]
    def call(name,slot=None):
        action=UpdateCall(name,slot);calls.append(action)
        result=execute(action,s)
        # Child effects represent writes to original binary32 owner fields.
        # Round them before the caller consumes a threshold or another stage.
        _normalize_state(s)
        return result
    def project_velocity():
        s.local_linear=transform(s.linear_velocity,s.to_local)
    def angular_world():
        s.angular_acceleration=transform(s.local_angular_acceleration,s.to_world)
    def tail():
        call('post_vehicle')
        if call('followup_enabled') and call('followup_ready'):call('followup')
    mode=call('global_mode')
    if not s.active:return VehicleUpdateOutput(s,tuple(calls),'inactive')
    if mode:
        s.speed=s.alternate_speed
        s.local_angular=transform(s.angular_velocity,s.to_local);project_velocity()
        call('predict_support');call('prepare_vehicle');call('control_update')
        steering=f32(s.maximum_steering*call('steering_angle'))
        call('project_wheels')
        for i,w in enumerate(s.wheels):
            w.force=ZERO
            if w.contact:w.force=(0.,f32(s.mass*f32(2.4525)),0.)
            if i<2:w.primary_angle=steering
            if w.spin_scale!=0:
                ratio=w.projected_speed/w.spin_scale
                w.spin=f32(ratio)
                w.phase=f32(ratio*f32(.004973592)+w.phase)
        call('engine')
        return VehicleUpdateOutput(s,tuple(calls),'alternate')
    call('prepare_vehicle')
    s.turning_radius_y=4000000. if s.angular_velocity[1]==0 else f32(s.linear_velocity[2]/(s.angular_velocity[1]*f32(6.2831855)))
    s.turning_radius_x=4000000. if s.angular_velocity[0]==0 else f32(s.linear_velocity[2]/(s.angular_velocity[0]*f32(6.2831855)))
    x,_,z=s.local_linear
    s.speed=f32(math.sqrt(x*x+z*z))
    if z<0:s.speed=-s.speed
    s.secondary_angle=f32(math.atan2(x,abs(z))*.15915493667125702)
    call('predict_support');call('support_bookkeeping')
    if s.tilted or s.attitude<f32(.85):
        for w in s.wheels:
            if not w.contact or w.force[1]==0:w.force=ZERO
        call('tilted_motion');call('refresh_motion');project_velocity();tail()
        return VehicleUpdateOutput(s,tuple(calls),'tilted')
    if s.flags&0x202:
        call('flagged_motion')
        return VehicleUpdateOutput(s,tuple(calls),'flagged')
    if sum(w.contact for w in s.wheels)<2:
        for w in s.wheels:w.force=ZERO
        call('body_forces')
        s.local_acceleration=(0.,f32(-s.gravity_force*s.inverse_mass),0.)
        s.linear_acceleration=transform(s.local_acceleration,s.to_world)
        call('linear_update');call('body_moment_inputs')
        if call('airborne_mode'):
            s.local_angular=tuple(f32(v*f32(.995)) for v in s.local_angular)
            moment=0.
        else:
            moment=f32(((2*s.front_lever*s.front_moment-2*s.rear_lever*s.rear_moment)+s.body_moment)*s.angular_scale*f32(.15915494))
        s.local_angular_acceleration=(moment,0.,0.)
        angular_world()
        s.angular_velocity=_increment(s.angular_velocity,s.angular_acceleration)
        call('refresh_motion');tail()
        return VehicleUpdateOutput(s,tuple(calls),'low_support')
    s.local_acceleration=transform(s.linear_acceleration,s.to_local)
    extra=transform(s.extra_acceleration,s.to_local)
    s.local_acceleration=tuple(f32(a+b) for a,b in zip(s.local_acceleration,extra))
    call('normal_loads')
    environment=s.environment_mode;absolute_speed=abs(s.speed)
    for i,w in enumerate(s.wheels):
        w.surface_class=s.fallback_surface if w.surface_record is None else w.surface_record&31
        if s.flags&0x200 or call('global_mode'):
            w.primary_coefficient=w.base_grip;w.secondary_coefficient=f32(w.base_grip*f32(.8))
            continue
        if environment==2:low,high=.01,.2
        elif environment==1 or w.surface_class in (6,20):low,high=.55,.95 if w.wear_mode==1 else .7
        else:low,high=.7,1.05
        factor=max(f32(low),min(f32(high),f32(f32(high)-(absolute_speed-f32(13.889))*f32(.0045))))
        factor=f32(factor*w.base_grip)
        if w.tire_type==5 and w.surface_class not in (1,10):factor=f32(factor*.25)
        factor=f32(max(f32(.95),min(f32(1.05),w.quality))*factor)
        axle_grip=s.front_grip_gate if i<2 else s.rear_grip_gate
        boost=False
        if axle_grip>f32(.1):boost=call('grip_observation',i)<f32(.7) and environment==0
        if boost or s.grip_boost:factor=f32(factor*f32(1.05))
        primary=factor*s.surface_coefficients[w.surface_class]
        w.primary_coefficient=f32(primary)
        w.secondary_coefficient=f32(primary*f32(.8))
        mismatch=abs(f32(w.spin_scale*w.spin-w.projected_speed))
        reduced=f32(math.exp((mismatch+abs(w.local_lateral))*f32(-.016666668))*w.primary_coefficient)
        floor=f32(w.primary_coefficient*.5)
        w.secondary_coefficient=min(w.secondary_coefficient,max(reduced,floor))
    if not call('vehicle_gate'):
        s.local_linear=ZERO;s.local_acceleration=ZERO;s.local_angular=ZERO;s.local_angular_acceleration=ZERO
    else:project_velocity()
    s.local_angular=transform(s.angular_velocity,s.to_local)
    for stage in ('project_wheels','control_update','body_moment_inputs','body_forces'):call(stage)
    acceleration=transform(s.linear_acceleration,s.to_local)
    s.local_acceleration=(acceleration[0],0.,acceleration[2])
    for stage in ('load_transfer','suspension_loads','resistance','engine','brakes','tires','wheel_correction'):call(stage)
    if call('vehicle_gate'):
        call('wheel_spin');call('combined_slip')
    for w in s.wheels:
        if w.clear_threshold < -w.clear_reference:w.force=ZERO
    if not s.orientation_disabled:call('force_orientation')
    call('body_moments')
    order=(s.wheels[2],s.wheels[3],s.wheels[1],s.wheels[0])
    if sum(w.force[1] for w in order)*f32(.101936795)<=0:
        local=(s.lateral_contribution,f32(-s.inverse_mass*s.gravity_force),f32(s.inverse_mass*s.longitudinal_contribution))
    else:
        local=(f32((sum(w.force[0] for w in order)+s.lateral_contribution)*s.inverse_mass*f32(1.1)),
               f32(-s.inverse_mass*s.gravity_force),f32((sum(w.force[2] for w in order)+s.longitudinal_contribution)*s.inverse_mass))
    s.local_acceleration=local
    angular_world()
    s.angular_velocity=transform(s.local_angular,s.to_world)
    s.angular_velocity=_increment(s.angular_velocity,s.angular_acceleration)
    if abs(s.local_acceleration[0])<f32(.001):s.local_acceleration=(0.,*s.local_acceleration[1:])
    s.linear_acceleration=transform(s.local_acceleration,s.to_world)
    call('linear_update')
    if s.support_count>2 and abs(s.speed)<6:
        angular=transform(s.angular_velocity,s.to_local)
        if abs(angular[1])<f32(.0027777778):angular=(angular[0],0.,angular[2])
        s.angular_velocity=transform(angular,s.to_world)
    tail()
    return VehicleUpdateOutput(s,tuple(calls),'supported')
