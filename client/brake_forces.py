"""Complete 0x538960 numeric brake update with explicit external effect records."""
from dataclasses import dataclass,replace
import math
from client.brake_thermal import BrakeThermalState,BrakeWorkWheel,update_brake_thermal,brake_fade
from client.tire_response import f32


@dataclass(frozen=True)
class BrakeForceWheel:
    spin_value: float
    spin_adjustment: float
    spin_scale: float
    projected_speed: float
    normal_load: float
    longitudinal_force: float
    control_angle: float
    component_code: int
    inertia_addend: float
    inertia_multiplier: float


@dataclass(frozen=True)
class BrakeForceState:
    thermal: BrakeThermalState
    wheels: tuple[BrakeForceWheel,...]
    front_quality: float
    rear_quality: float
    front_gate: float
    rear_gate: int
    rear_distribution: float
    drive_factor: float
    pitch_angle: float
    vehicle_code: int
    auxiliary_flag: bool
    parking_ramp: int


@dataclass(frozen=True)
class BrakeForceOutput:
    state: BrakeForceState
    # Ordered original effect calls. Component-event delivery and controller
    # hardware behavior are external, rather than discarded or invented.
    wear_events: tuple[tuple[int,float],...]
    controller_events: tuple[int,...]


def update_brake_forces(state):
    if len(state.wheels)!=4 or len(state.thermal.wheels)!=4:
        raise ValueError('four brake wheel records required')
    if type(state.auxiliary_flag) is not bool or type(state.parking_ramp) is not int or not 0<=state.parking_ramp<=64:
        raise ValueError('boolean auxiliary mode and parking ramp in [0,64] required')
    for value in (state.rear_gate,state.vehicle_code,*(w.component_code for w in state.wheels)):
        if type(value) is not int or not -0x80000000<=value<=0x7fffffff:
            raise ValueError('signed int32 gate and component codes required')
    front_quality,rear_quality,front_gate,rear_distribution,drive,pitch=map(f32,
        (state.front_quality,state.rear_quality,state.front_gate,state.rear_distribution,state.drive_factor,state.pitch_angle))
    wheels=[]
    for w in state.wheels:
        values=tuple(map(f32,(w.spin_value,w.spin_adjustment,w.spin_scale,w.projected_speed,
            w.normal_load,w.longitudinal_force,w.control_angle,w.inertia_addend,w.inertia_multiplier)))
        if values[2]<=0 or values[4]<0:
            raise ValueError('positive spin scale and nonnegative load required')
        wheels.append(BrakeForceWheel(*values[:7],w.component_code,*values[7:]))
    thermal=update_brake_thermal(replace(state.thermal,wheels=tuple(BrakeWorkWheel(old.brake_force,
        w.spin_scale,w.spin_value) for old,w in zip(state.thermal.wheels,wheels))))
    service,speed=thermal.service_control,abs(thermal.speed)
    forces=[0.0]*4
    enabled=[True]*4
    wear,controller=[],[]
    ramp=state.parking_ramp
    if service!=0 or thermal.parking_control or state.auxiliary_flag:
        for i,w in enumerate(wheels):
            axle=thermal.front if i<2 else thermal.rear
            strength=0.0
            if service!=0:
                cold=f32(.8) if axle.material_code==3 and axle.temperature<160 else 1.0
                if axle.temperature>axle.temperature_limit:
                    wear.append((i,f32((axle.temperature-axle.temperature_limit)*f32(2.6041666e-6))))
                fade=brake_fade(axle.temperature,axle.temperature_limit)
                quality=min(front_quality if i<2 else rear_quality,.5)
                strength=f32((1-quality)*fade*cold*service)
            if strength==0 and not (thermal.parking_control or state.auxiliary_flag):
                enabled=[False]*4
                continue
            spin_motion=f32(w.spin_value*32+w.spin_adjustment)
            inertia=f32(drive*w.inertia_multiplier*.5+w.inertia_addend)
            if inertia==0:
                raise ValueError('nonzero derived inertia required')
            drag=abs(f32(inertia*w.spin_adjustment))
            special=w.component_code in (6,20) or state.vehicle_code==1
            radius=f32(axle.diameter*.5)
            material=f32({0:.85,1:.9,2:.95}.get(axle.material_code,1.0))
            capacity=f32(material*radius*radius*f32(3.1415927)*f32(16.310127)*2500
                *(strength if i<2 else (rear_distribution*strength if not (thermal.parking_control or state.auxiliary_flag) else 1.0)))
            if axle.construction_code==1:
                capacity=f32(capacity*f32(.98))
                if special:capacity=f32(capacity*f32(.8))
            parking=i>=2 and (thermal.parking_control or state.auxiliary_flag)
            if parking:
                ramp=min(ramp+4,64)
                # Parking torque uses the base wheel inertia, not drive coupling.
                inertia=w.inertia_addend
                if inertia==0:raise ValueError('nonzero parking inertia required')
                signed=-capacity if w.projected_speed>0 else capacity
                forces[i]=f32(signed/w.spin_scale)
                available=f32(abs(spin_motion)*inertia)
                torque=min(available,signed) if w.projected_speed<=0 else max(-available,signed)
                adjustment=f32(torque/inertia)
            else:
                torque=capacity
                if speed>1:
                    reduction=min(drag,f32(capacity*.5))
                    if abs(w.spin_value)<f32(.05):torque=f32(capacity-reduction)
                else:
                    cosine=math.cos(pitch*f32(6.2831855))
                    if cosine==0:raise ValueError('nonzero pitch cosine required')
                    static=f32(thermal.mass_parameter*f32(.00066666666)*(f32(.12 if i<2 else .082)/cosine)*capacity)
                    rolling=f32(w.normal_load*w.spin_scale*speed*strength*f32(3.2619774))
                    torque=max(abs(static),rolling) if i<2 else abs(max(static,rolling))
                gate=front_gate!=0 if i<2 else state.rear_gate!=0
                if not gate or w.control_angle>f32(-.4):
                    forces[i]=f32(torque/w.spin_scale)
                    adjustment=f32(torque/inertia)
                    if axle.material_code in (2,3):
                        controller.append(round(f32(strength*(64 if i>=2 and axle.material_code==2 else 127))))
                else:
                    enabled[i]=False
                    adjustment=0.0
                if i>=2:ramp=0
            limit=abs(spin_motion)
            adjustment=max(-limit,min(limit,adjustment))
            if w.spin_value<=0:adjustment=min(abs(adjustment),f32(w.spin_value*-32))
            else:adjustment=max(-abs(adjustment),f32(w.spin_value*-32))
            if front_gate!=0 and not all(enabled[:2]):enabled[0]=enabled[1]=False
            if state.rear_gate!=0 and not all(enabled[2:]):enabled[2]=enabled[3]=False
            if speed<=1:forces[i]=f32(-(w.projected_speed*thermal.mass_parameter)*8)
            gate=front_gate!=0 if i<2 else state.rear_gate!=0
            longitudinal=w.longitudinal_force
            if not gate or enabled[i]:
                spin_adjustment=f32(w.spin_adjustment+adjustment*(.25 if gate else .5))
                if w.normal_load!=0:
                    longitudinal=f32(longitudinal+(abs(forces[i]) if w.projected_speed<=0 else -abs(forces[i])))
            else:spin_adjustment=w.spin_adjustment
            wheels[i]=replace(w,spin_adjustment=spin_adjustment,longitudinal_force=longitudinal)
    thermal=replace(thermal,wheels=tuple(replace(w,brake_force=forces[i]) for i,w in enumerate(thermal.wheels)))
    result=replace(state,thermal=thermal,wheels=tuple(wheels),front_quality=front_quality,rear_quality=rear_quality,
        front_gate=front_gate,rear_distribution=rear_distribution,drive_factor=drive,pitch_angle=pitch,parking_ramp=ramp)
    return BrakeForceOutput(result,tuple(wear),tuple(controller))
