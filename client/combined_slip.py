"""Complete original 0x53fb30 numeric force limiting and ordered effect observations."""
from dataclasses import dataclass,replace
import math
from client.tire_response import f32


@dataclass(frozen=True)
class CombinedSlipWheel:
    slip_ratio: float
    lateral_force: float
    longitudinal_force: float
    secondary_response: float
    normal_load: float
    primary_coefficient: float
    secondary_coefficient: float
    spin_value: float
    spin_scale: float
    projected_speed: float
    contact: bool
    component_code: int
    wear_mode: int


@dataclass(frozen=True)
class CombinedSlipState:
    wheels: tuple[CombinedSlipWheel,...]
    speed: float
    parking_control: bool
    alternate_mode: bool
    front_quality: float
    rear_quality: float
    vehicle_code: int


@dataclass(frozen=True)
class SlipEffect:
    operation: int  # 0: component update, 1: secondary component observation
    slot: int
    amount: float
    parameter_a: float = 0
    parameter_b: float = 0
    parameter_c: float = 0


def longitudinal_slip_factor(slip):
    s=f32(slip)
    if s>=0:
        if s<=f32(.15):return 1.0
        if s<1:return f32((1-s)*f32(.4117647)+f32(.65))
        if s<=8:return f32(f32(.7071)-s*f32(.0571))
        return max(.0625,f32(2/s))
    if s>=f32(-.05):return 1.0
    if s>=f32(-.2):return f32(s*f32(-4.375))
    if s>-1:return f32(f32(.875)-abs(f32(s*f32(.375))))
    return max(.125,abs(f32(.5/s)))


def limit_combined_slip(state):
    if len(state.wheels)!=4:raise ValueError('four wheel records required')
    speed,front,rear=map(f32,(state.speed,state.front_quality,state.rear_quality))
    if type(state.parking_control) is not bool or type(state.alternate_mode) is not bool:
        raise ValueError('boolean modes required')
    wheels=[]
    for w in state.wheels:
        values=tuple(map(f32,(w.slip_ratio,w.lateral_force,w.longitudinal_force,w.secondary_response,
            w.normal_load,w.primary_coefficient,w.secondary_coefficient,w.spin_value,w.spin_scale,w.projected_speed)))
        if values[8]<=0 or min(values[4:7])<0:raise ValueError('positive spin scale and nonnegative capacities required')
        if type(w.contact) is not bool:raise ValueError('boolean contact required')
        wheels.append(CombinedSlipWheel(*values,w.contact,w.component_code,w.wear_mode))
    if not state.parking_control:
        left,right=wheels[3],wheels[2]
        lc=f32(left.normal_load*left.primary_coefficient);rc=f32(right.normal_load*right.primary_coefficient)
        if left.longitudinal_force>lc and right.longitudinal_force<rc:
            delta=min(f32(left.longitudinal_force-lc),f32(rc-right.longitudinal_force))
            wheels[3]=replace(left,longitudinal_force=f32(left.longitudinal_force-delta))
            wheels[2]=replace(right,longitudinal_force=f32(right.longitudinal_force+delta))
        elif right.longitudinal_force>rc and left.longitudinal_force<lc:
            delta=min(f32(right.longitudinal_force-rc),f32(lc-left.longitudinal_force))
            wheels[3]=replace(left,longitudinal_force=f32(left.longitudinal_force+delta))
            wheels[2]=replace(right,longitudinal_force=f32(right.longitudinal_force-delta))
    effects=[]
    def observe_loss(i,loss):
        w=wheels[i];loss=f32(loss)
        if loss==0 or w.normal_load==0 or w.primary_coefficient==0 or not w.contact:return
        if w.component_code not in (6,20) and state.vehicle_code==0 and w.wear_mode==1:
            effects.append(SlipEffect(0,i,f32(5.2083333e-6),0,1,.25))
        amount=max(0,min(w.primary_coefficient,f32(loss*w.primary_coefficient)))
        if amount>0 and w.slip_ratio>0 and speed>0:
            mismatch=min(f32(13.4109),abs(f32(w.spin_value-w.projected_speed/w.spin_scale)))
            effects.append(SlipEffect(0,i,amount,f32(.15),f32(.000052083335),.25))
            effects.append(SlipEffect(1,i,f32(mismatch*.03125)))
    for i,w in enumerate(wheels):
        factor=longitudinal_slip_factor(w.slip_ratio) if speed>1 else 1.0
        observe_loss(i,f32(1-factor))
        longitudinal=f32(factor*w.longitudinal_force)
        if w.slip_ratio<f32(-.05):longitudinal=f32((1-(front if i<2 else rear)*.5)*factor*w.longitudinal_force)
        magnitude=f32(math.sqrt(w.lateral_force*w.lateral_force+longitudinal*longitudinal))
        capacity=f32(w.primary_coefficient*w.normal_load)
        secondary_capacity=f32(w.secondary_coefficient*w.normal_load)
        if state.alternate_mode:
            capacity=f32(capacity*factor);secondary_capacity=f32(secondary_capacity*factor)
        lateral,secondary=w.lateral_force,w.secondary_response
        if capacity<magnitude and magnitude>0:
            reduction=f32(math.sqrt(f32((secondary_capacity/magnitude)*f32(.99))))
            observe_loss(i,f32(1-reduction))
            lateral=f32(reduction*lateral);longitudinal=f32(reduction*longitudinal)
            secondary=f32((secondary_capacity/magnitude)*secondary)
        wheels[i]=replace(w,lateral_force=lateral,longitudinal_force=longitudinal,secondary_response=secondary)
    return replace(state,wheels=tuple(wheels)),tuple(effects)
