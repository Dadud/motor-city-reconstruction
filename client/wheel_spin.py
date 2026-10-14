"""Original 0x5400b0 wheel state integration with external component effects."""
from dataclasses import dataclass,replace
from client.tire_response import f32


@dataclass(frozen=True)
class SpinWheel:
    spin_value: float
    spin_adjustment: float
    spin_scale: float
    projected_speed: float
    normal_load: float
    kinetic_parameter: float
    ratio_denominator: float
    phase: float
    correction_enabled: bool
    contact: bool
    secondary_angle: float = 0
    slip_ratio: float = 0
    kinetic_value: float = 0
    local_lateral: float = 0
    local_vertical: float = 0
    local_longitudinal: float = 0


@dataclass(frozen=True)
class WheelSpinState:
    wheels: tuple[SpinWheel,...]
    direction_mode: int
    override_control: bool
    rpm: int
    gear_multiplier: float
    front_scale: float
    rear_scale: float
    front_compliance: float
    rear_compliance: float
    front_secondary_angle: float
    rear_secondary_angle: float
    front_quality: float
    rear_quality: float
    body_secondary_angle: float
    front_lever: float
    rear_lever: float
    yaw_rate: float
    lateral_velocity: float


@dataclass(frozen=True)
class WheelSpinOutput:
    state: WheelSpinState
    wear_events: tuple[tuple[int,float],...]


def integrate_wheel_spin(state):
    if len(state.wheels)!=4 or type(state.direction_mode) is not int or not 0<=state.direction_mode<=255:
        raise ValueError('four records and byte direction mode required')
    if type(state.rpm) is not int or not -0x80000000<=state.rpm<=0x7fffffff:
        raise ValueError('signed int32 RPM required')
    if type(state.override_control) is not bool:
        raise ValueError('boolean override required')
    multiplier,front,rear,fc,rc,fa,ra,fq,rq,body,fl,rl,yaw,lateral=map(f32,
        (state.gear_multiplier,state.front_scale,state.rear_scale,state.front_compliance,state.rear_compliance,
         state.front_secondary_angle,state.rear_secondary_angle,state.front_quality,state.rear_quality,
         state.body_secondary_angle,state.front_lever,state.rear_lever,state.yaw_rate,state.lateral_velocity))
    if min(front,rear)<=0 or min(fc,rc)<0:raise ValueError('positive axle scales and nonnegative compliance required')
    wheels,events=[],[]
    for i,w in enumerate(state.wheels):
        spin,adjustment,scale,speed,load,kinetic,denominator,phase=map(f32,
            (w.spin_value,w.spin_adjustment,w.spin_scale,w.projected_speed,w.normal_load,
             w.kinetic_parameter,w.ratio_denominator,w.phase))
        if scale<=0 or denominator==0 or load<0:raise ValueError('positive scale/nonzero denominator/nonnegative load required')
        if type(w.contact) is not bool or type(w.correction_enabled) is not bool:raise ValueError('boolean flags required')
        spin=f32(spin+adjustment*.03125)
        if w.correction_enabled and not state.override_control and state.direction_mode!=1:
            limit=f32(max(abs(speed/scale),abs(f32(state.rpm)*multiplier/scale)))
            spin=max(-limit,min(limit,spin))
        deformation=max(0,min(f32(.05),f32(load*f32(.001)*f32(.005))))
        squared=f32(spin*spin)
        kinetic_value=f32(squared*kinetic*.5)
        base,compliance=(front,fc) if i<2 else (rear,rc)
        delta=f32(deformation-squared*base*f32(.101936795)*compliance*f32(.001))
        delta=max(f32(-.01),min(compliance,delta))
        scale=f32(base-delta)
        phase=f32(spin*f32(.004973592)+phase)
        forward=f32(scale*spin)
        # The stored forward output and the continuing x87 product differ:
        # the event ratio divides the product before its float32 store.
        ratio=f32(scale*spin/denominator)
        local=f32(fl*yaw+lateral) if i<2 else f32(lateral-rl*yaw)
        if ratio>1:events.append((i,f32(ratio*f32(5.2083337e-6))))
        slip=0 if speed==0 else f32((scale*spin-speed)/speed)
        slip=max(-1.0,min(100000.0,slip))
        secondary=f32((fa if i<2 else ra)*f32(.0055555557))
        if w.contact:secondary=f32(abs(body*f32(1.05 if i<2 else 1.02))+secondary)
        quality=fq if i<2 else rq
        if quality>.75:secondary=f32((.75-quality)*f32(.07)+secondary)
        secondary=max(f32(-.083333336),min(f32(.083333336),secondary))
        wheels.append(replace(w,spin_value=spin,spin_adjustment=adjustment,spin_scale=scale,projected_speed=speed,
            normal_load=load,kinetic_parameter=kinetic,ratio_denominator=denominator,phase=phase,
            secondary_angle=secondary,slip_ratio=slip,kinetic_value=kinetic_value,
            local_lateral=local,local_vertical=0,local_longitudinal=forward))
    return WheelSpinOutput(replace(state,wheels=tuple(wheels)),tuple(events))
