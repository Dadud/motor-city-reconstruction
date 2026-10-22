"""Original 0x53ecf0 tire update with explicit per-wheel mode observations.

Consecutive wheel-record order is preserved. Component curve production and
global mode-query delivery are external; this is not a complete vehicle tick.
"""
from dataclasses import dataclass, replace
import math
import struct
from client.steering_response import steering_response
from client.tire_response import WheelCurveInput, wheel_response, f32


@dataclass(frozen=True)
class TireCurves:
    primary: tuple[float, ...]
    secondary: tuple[float, ...]
    angle_coefficient: float

    @classmethod
    def from_assembled_configuration(cls, image, axle):
        """Read the 26-knot curves produced by the native tire loader.

        The first curve begins at configuration +0x150 (front) or +0x254
        (rear); its companion begins at +0x1b8 or +0x2bc. Each includes the
        loader's leading zero followed by 25 Pacejka auxiliary values.
        """
        if len(image) != 0x820:
            raise ValueError('expected assembled 0x820-byte vehicle configuration')
        if axle not in ('front', 'rear'):
            raise ValueError("axle must be 'front' or 'rear'")
        base = 0x148 if axle == 'front' else 0x24c
        coefficient = struct.unpack_from('<f', image, base)[0]
        primary = struct.unpack_from('<26f', image, base + 8)
        secondary = struct.unpack_from('<26f', image, base + 0x70)
        if not all(math.isfinite(value) for value in
                   (coefficient, *primary, *secondary)):
            raise ValueError('assembled tire response contains a non-finite value')
        return cls(primary, secondary, coefficient)


@dataclass(frozen=True)
class TireWheel:
    steering_angle: float
    slip_angle: float
    secondary_angle: float
    projected_speed: float
    normal_load: float
    contact: bool
    surface_multiplier: float
    lateral_force: float
    longitudinal_force: float
    secondary_response: float


@dataclass(frozen=True)
class TireUpdateState:
    wheels: tuple[TireWheel, ...]
    front_curves: TireCurves
    rear_curves: TireCurves
    raw_control: int
    speed: float
    mass_parameter: float
    front_lever: float
    rear_lever: float
    front_track: float
    wheelbase: float
    maximum_steering: float
    longitudinal_velocity: float
    lateral_velocity: float
    lateral_acceleration: float
    yaw_rate: float
    body_slip: float
    rear_steering: bool
    mode_observations: tuple[bool, bool, bool, bool]
    alternate_load: bool = False


def _curves(curves):
    if len(curves.primary) != 26 or len(curves.secondary) != 26:
        raise ValueError('two 26-knot axle curves required')
    return TireCurves(tuple(map(f32,curves.primary)),tuple(map(f32,curves.secondary)),f32(curves.angle_coefficient))


def update_tires(state: TireUpdateState):
    if len(state.wheels)!=4 or len(state.mode_observations)!=4 or any(type(x) is not bool for x in state.mode_observations):
        raise ValueError('four wheel records and boolean mode observations required')
    front_curves,rear_curves=_curves(state.front_curves),_curves(state.rear_curves)
    speed,mass,front,rear,track,wheelbase,maximum,velocity,lateral,acceleration,yaw,body_slip=map(f32,
        (state.speed,state.mass_parameter,state.front_lever,state.rear_lever,state.front_track,
         state.wheelbase,state.maximum_steering,state.longitudinal_velocity,state.lateral_velocity,
         state.lateral_acceleration,state.yaw_rate,state.body_slip))
    if min(track,wheelbase,mass)<=0:
        raise ValueError('positive dimensions and mass parameter required')
    wheels=[]
    for w in state.wheels:
        if type(w.contact) is not bool:
            raise ValueError('boolean wheel contact required')
        values=tuple(map(f32,(w.steering_angle,w.slip_angle,w.secondary_angle,w.projected_speed,
                             w.normal_load,w.surface_multiplier,w.lateral_force,w.longitudinal_force,w.secondary_response)))
        if values[4]<0:
            raise ValueError('nonnegative normal load required')
        wheels.append(TireWheel(*values[:5],w.contact,*values[5:]))
    steering=f32(maximum*steering_response(state.raw_control,velocity))
    turn=f32(6.2831855)
    inverse_turn=0.15915493667125702
    angles=[steering,steering,0.0,0.0]
    if abs(steering)>=f32(0.001):
        radians=abs(steering)*turn
        tangent=f32(math.sin(radians))/f32(math.cos(radians))
        denominator=f32(wheelbase/tangent-track)
        paired=f32(math.atan2(wheelbase,denominator)*inverse_turn)
        if steering<=0:
            angles[0]=-paired
        else:
            angles[1]=paired
    if state.rear_steering:
        if abs(speed)<=f32(8.9406):
            rear_angle=max(f32(-0.055555556),min(f32(0.055555556),f32(steering*f32(-0.2))))
        else:
            rear_angle=max(f32(-0.027777778),min(f32(0.027777778),f32(steering*0.5)))
        angles[2]=angles[3]=rear_angle
    angles=[max(-1.0,min(1.0,angle)) for angle in angles]
    if abs(speed)<=0.25:
        yaw=f32(yaw*f32(0.95))
        acceleration=f32(lateral*-32.0)
        lateral=0.0
    result=[]
    for i,w in enumerate(wheels):
        slip=0.0
        if state.mode_observations[i]:
            lever=front if i<2 else rear
            numerator=f32(lever*yaw*turn)
            angle=math.atan2(numerator,abs(velocity))*inverse_turn
            slip=f32(angle+body_slip if i<2 else body_slip-angle)
        slip=f32(slip-angles[i] if w.projected_speed>=0 else slip+angles[i])
        force,longitudinal,secondary=0.0,w.longitudinal_force,0.0
        if w.normal_load<=0 or not w.contact:
            longitudinal=0.0
        elif abs(speed)>=0.25:
            if abs(speed)<6.0:
                blend=f32((abs(speed)-0.25)*f32(0.17391305))
                slip=f32(blend*slip+(1.0-blend)*math.sin(slip*turn)*f32(0.008333334))
                slip=max(-1.0,min(1.0,slip))
            curves=front_curves if i<2 else rear_curves
            observation=WheelCurveInput(slip,w.secondary_angle,w.normal_load,w.surface_multiplier)
            force=wheel_response(curves.primary,curves.angle_coefficient,observation,alternate_load=state.alternate_load)
            secondary=wheel_response(curves.secondary,curves.angle_coefficient,observation,secondary=True)
            if abs(lateral)<0.25:
                force=f32(force-lateral*f32(1.4)*math.sqrt(w.normal_load*5700.0))
        else:
            force=f32(mass*0.25*acceleration)
        if abs(force)<=10.0 and abs(speed)>6.0:
            force=0.0
        result.append(replace(w,steering_angle=angles[i],slip_angle=slip,lateral_force=force,
                              longitudinal_force=longitudinal,secondary_response=secondary))
    return replace(state,wheels=tuple(result),front_curves=front_curves,rear_curves=rear_curves,
        speed=speed,mass_parameter=mass,front_lever=front,rear_lever=rear,front_track=track,
        wheelbase=wheelbase,maximum_steering=maximum,longitudinal_velocity=velocity,
        lateral_velocity=lateral,lateral_acceleration=acceleration,yaw_rate=yaw,body_slip=body_slip)
