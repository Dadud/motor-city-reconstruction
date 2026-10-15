"""Original 0x536480 arithmetic with explicit environment and drafting inputs."""
from dataclasses import dataclass
import math
from client.tire_response import f32


@dataclass(frozen=True)
class BodyResistanceState:
    speed: float
    longitudinal_speed: float
    drag_parameter: float
    accessory_parameter: bool
    accessory_enabled: bool
    drag_adjustment: float
    vehicle_code: int
    secondary_angle: float
    area_parameter: float
    density: float
    wind_lateral: float
    wind_longitudinal: float
    drafting_factor: float
    resistance_disabled: bool
    pitch_angle: float
    length_parameter: float
    height_parameter: float
    load_transfer_disabled: bool
    front_lever: float
    rear_lever: float
    downforce_parameter: float
    configuration_downforce: float
    wheel_loads: tuple[float, ...]
    contacts: tuple[bool, ...]


@dataclass(frozen=True)
class BodyResistanceOutput:
    longitudinal_drag: float
    yaw_contribution: float
    pitch_contribution: float
    wheel_loads: tuple[float, ...]


def calculate_body_resistance(s: BodyResistanceState) -> BodyResistanceOutput:
    if len(s.wheel_loads)!=4 or len(s.contacts)!=4:
        raise ValueError('four consecutive wheel loads and contact flags required')
    for value in (s.accessory_parameter,s.accessory_enabled,s.resistance_disabled,s.load_transfer_disabled,*s.contacts):
        if type(value) is not bool: raise ValueError('boolean mode required')
    speed,longitudinal_speed,drag,adjustment,angle,area,density,wx,wz,draft,pitch,length,height,front,rear,down,cd=map(f32,(
        s.speed,s.longitudinal_speed,s.drag_parameter,s.drag_adjustment,s.secondary_angle,s.area_parameter,
        s.density,s.wind_lateral,s.wind_longitudinal,s.drafting_factor,s.pitch_angle,s.length_parameter,
        s.height_parameter,s.front_lever,s.rear_lever,s.downforce_parameter,s.configuration_downforce))
    if front==0 or rear==0: raise ValueError('nonzero lever parameters required')
    loads=list(map(f32,s.wheel_loads))
    if s.accessory_parameter and s.accessory_enabled: drag=f32(drag+f32(.02))
    if adjustment!=0: drag=f32(drag*(adjustment*.5+1))
    rate,cap,lateral=(.003,1.12,6) if s.vehicle_code==6 else ((.0125,1.5,10) if s.vehicle_code<=3 else (.006,1.24,8))
    multiplier=min(f32(cap),f32(abs(f32(angle*180))*f32(rate)+1))
    relative=f32(abs(speed)-wz)
    magnitude=0.0 if s.resistance_disabled else f32(relative*relative*density*area*multiplier*drag*.5)
    magnitude=f32(magnitude*draft)
    longitudinal=-magnitude if longitudinal_speed>=0 else magnitude
    yaw=f32(wx*wx*lateral*density*area*(-.5 if wx<0 else .5))
    moment=(height*f32(.9090909)+math.sin(pitch*f32(6.2831855))*length)*magnitude
    stored_moment=0.0 if s.resistance_disabled else f32(moment)
    if not s.load_transfer_disabled:
        half=moment*.5
        front_delta=f32(half/front)
        for i in (0,1): loads[i]=max(0.0,f32(loads[i]-front_delta))
        rear_delta=f32(f32(half)/rear)
        loads[3]=max(0.0,f32(loads[3]+f32(half)/rear))
        loads[2]=max(0.0,f32(loads[2]+rear_delta))
        if all(s.contacts):
            change=(down+cd)*relative*relative*density*area*(-.5)*.25
            stored_change=f32(change)
            loads[0]=max(0.0,f32(loads[0]+change))
            for i in (1,3,2): loads[i]=max(0.0,f32(loads[i]+stored_change))
    return BodyResistanceOutput(longitudinal,yaw,stored_moment,tuple(loads))
