"""Recovered thermal/initialization stage of 0x538960, not complete brake forces."""
from dataclasses import dataclass, replace

from client.tire_response import f32


@dataclass(frozen=True)
class BrakeThermalAxle:
    temperature: float
    diameter: float
    cooling_coefficient: float
    heat_capacity_factor: float
    thermal_mass: float
    temperature_limit: float
    material_code: int
    construction_code: int
    countdown: int


@dataclass(frozen=True)
class BrakeWorkWheel:
    brake_force: float
    spin_scale: float
    spin_value: float


@dataclass(frozen=True)
class BrakeThermalState:
    front: BrakeThermalAxle
    rear: BrakeThermalAxle
    wheels: tuple[BrakeWorkWheel, ...]
    service_control: float
    parking_control: bool
    speed: float
    mass_parameter: float
    elevation_parameter: float
    environment_flag: bool
    environment_code: int
    kinetic_value: float = 0
    elevation_value: float = 0


def brake_countdown(diameter, material_code, construction_code):
    """Complete 0x539790 with original round-to-nearest-even integer store."""
    if type(material_code) is not int or not 0 <= material_code <= 0xffffffff:
        raise ValueError('uint32 material code required')
    if type(construction_code) is not int or not 0 <= construction_code <= 0xffffffff:
        raise ValueError('uint32 construction code required')
    diameter=f32(diameter)
    return round(f32(diameter*f32(39.370098))) + {1:16,2:8,3:32}.get(material_code,0) + (8 if construction_code==1 else 0)


def brake_fade(temperature, limit):
    """Complete 0x539940, result in [0.5,1]."""
    temperature,limit=map(f32,(temperature,limit))
    if temperature<limit:return 1.0
    if limit+50<temperature:return .5
    return max(.5,min(1,f32((limit-temperature)*f32(.01)+1)))


def brake_ambient(environment_flag, environment_code):
    """0x539820 after an explicit observed world-state query result."""
    return (5 if environment_flag else 15)-({1:10,2:20}.get(environment_code,0))


def update_brake_thermal(state):
    """Thermal stage before0x538ca4; clears previous four brake-force outputs.

    Does not execute the subsequent brake force, wear, vibration or spin stage.
    """
    if len(state.wheels)!=4:raise ValueError('four wheel observations required')
    service,speed,mass,elevation=map(f32,(state.service_control,state.speed,
        state.mass_parameter,state.elevation_parameter))
    wheels=tuple(BrakeWorkWheel(*map(f32,(w.brake_force,w.spin_scale,w.spin_value))) for w in state.wheels)
    ambient=f32(brake_ambient(state.environment_flag,state.environment_code))
    front_work=rear_work=0
    if (service!=0 or state.parking_control) and abs(speed)>1:
        if service!=0:
            front_work=f32((abs(f32(wheels[0].brake_force*wheels[0].spin_scale*wheels[0].spin_value))+
                abs(f32(wheels[1].brake_force*wheels[1].spin_scale*wheels[1].spin_value)))*.03125)
        rear_speeds=tuple(abs(f32(w.spin_scale*w.spin_value)) for w in wheels[2:])
        if state.parking_control or service!=0 and max(rear_speeds)>1:
            rear_work=f32((abs(f32(rear_speeds[0]*wheels[2].brake_force))+
                abs(f32(rear_speeds[1]*wheels[3].brake_force)))*.03125)
    updated=[]
    for axle,work in ((state.front,front_work),(state.rear,rear_work)):
        temperature,diameter,cooling,capacity,thermal_mass,limit=map(f32,
            (axle.temperature,axle.diameter,axle.cooling_coefficient,axle.heat_capacity_factor,
             axle.thermal_mass,axle.temperature_limit))
        if min(capacity,thermal_mass)<=0:raise ValueError('positive thermal denominators required')
        if type(axle.countdown) is not int or not 0<=axle.countdown<=0x7fffffff:
            raise ValueError('nonnegative signed countdown required')
        countdown=brake_countdown(diameter,axle.material_code,axle.construction_code)+64 if service==0 else max(0,axle.countdown-1)
        cooling_work=(temperature-ambient)*diameter*diameter*.25*f32(3.1415927)*cooling*f32(abs(speed)+5)
        new_temperature=f32(temperature+(work-cooling_work)*f32(.001)/((thermal_mass+thermal_mass)*capacity))
        new_temperature=min(new_temperature,f32(limit+limit))
        updated.append(replace(axle,temperature=new_temperature,diameter=diameter,
            cooling_coefficient=cooling,heat_capacity_factor=capacity,thermal_mass=thermal_mass,
            temperature_limit=limit,countdown=countdown))
    return replace(state,front=updated[0],rear=updated[1],
        wheels=tuple(replace(w,brake_force=0) for w in wheels),service_control=service,speed=speed,
        mass_parameter=mass,elevation_parameter=elevation,kinetic_value=f32(speed*speed*mass*.5),
        elevation_value=f32(mass*elevation*f32(9.81)))
