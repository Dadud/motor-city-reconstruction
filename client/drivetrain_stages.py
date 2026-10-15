"""Recovered clutch, coupling preparation, request, drive and force application.

Field names describe consumers; unknown component units remain explicit. This
module does not initialize a stock car or implement component/service effects.
"""
from copy import deepcopy
from dataclasses import dataclass, field, fields, replace
from client.tire_response import f32
from client.driving_mode import vehicle_control_mode


@dataclass
class DriveWheel:
    spin: float = 0
    adjustment: float = 0
    radius: float = .3
    inertia: float = 1
    conversion: float = 1
    distribution: float = .5
    torque: float = 0
    normal_load: float = 3000
    longitudinal_force: float = 0
    driven: bool = True
    contact: bool = True


@dataclass
class DriveState:
    wheels: list = field(default_factory=lambda:[DriveWheel() for _ in range(4)])
    engine_flags: int = 1
    vehicle_flags: int = 4
    rpm: int = 3000
    gear: int = 2
    hold_ticks: int = 0
    override_byte: int = 0
    raw_throttle: int = 128
    auxiliary_byte: int = 0
    component_mode: int = 0
    mode_setting: int = 0
    local_player: bool = False
    bypass: bool = False
    throttle: float = .5
    engagement: float = .5
    clutch_gain: float = 0
    angular_speed: float = 300
    coupling_resistance: float = 0
    effective_torque: float = 100
    transmitted_torque: float = 0
    reference_rotation: float = 0
    output_torque: float = 0
    driven_speed: float = 0
    previous_rotation: float = 0
    drag_speed: float = 0
    prior_output_rotation: float = 0
    final_drive_acceleration: float = 0
    gearbox_drag: float = 0
    output_rotation: float = 0
    wheel_acceleration: float = 0
    accumulated_drag: float = 0
    inertia_sum: float = 1
    longitudinal_speed: float = 0
    acceleration: float = 0
    speed: float = 0
    alternate_speed: float = 0
    damage_one: float = 0
    damage_two: float = 0
    request: float = 0


@dataclass(frozen=True)
class DriveConfig:
    gear_ratios: tuple
    gear_losses: tuple
    inertia_factors: tuple
    speed_factors: tuple
    final_drive: float
    torque_capacity: float
    efficiency: float
    clutch_steps: int
    maximum_rpm: int
    third_enabled: bool
    option_one: float
    option_two: float
    option_kind: int
    increment_gain: float
    secondary_gain: float
    secondary_kind: int


@dataclass(frozen=True)
class DriveCall:
    stage: str
    code: int | None = None
    values: tuple = ()


def normalize(state):
    s=deepcopy(state)
    if len(s.wheels)!=4:raise ValueError('four drive wheels required')
    bools={'local_player','bypass'}
    ints={'engine_flags','vehicle_flags','rpm','gear','hold_ticks','override_byte','raw_throttle',
          'auxiliary_byte','component_mode','mode_setting'}
    for record in (s,*s.wheels):
        for f in fields(record):
            value=getattr(record,f.name)
            if f.name in bools or f.name in ('driven','contact'):
                if type(value) is not bool:raise ValueError('boolean drive observation required')
            elif f.name in ints:
                if type(value) is not int:raise ValueError('integer drive observation required')
            elif f.name!='wheels':setattr(record,f.name,f32(value))
    for n in ('engine_flags','vehicle_flags','mode_setting'):
        if not 0<=getattr(s,n)<=0xffffffff:raise ValueError('uint32 drive observation required')
    for n in ('override_byte','raw_throttle','auxiliary_byte'):
        if not 0<=getattr(s,n)<=255:raise ValueError('byte drive observation required')
    for n in ('rpm','gear','hold_ticks','component_mode'):
        if not -0x80000000<=getattr(s,n)<=0x7fffffff:raise ValueError('int32 drive observation required')
    return s


def configuration(c,s):
    if type(c.third_enabled) is not bool:raise ValueError('boolean shared configuration required')
    if type(c.clutch_steps) is not int or not 0<c.clutch_steps<=0x7fffffff:raise ValueError('positive int32 clutch step count required')
    for name in ('maximum_rpm','option_kind','secondary_kind'):
        value=getattr(c,name)
        if type(value) is not int or not -0x80000000<=value<=0x7fffffff:
            raise ValueError('int32 drive configuration required')
    for values in (c.gear_ratios,c.gear_losses,c.inertia_factors,c.speed_factors):
        if not 0<=s.gear<len(values):raise ValueError('explicit table entry required for RPM gear index')
    if c.final_drive==0 or c.torque_capacity==0:raise ValueError('nonzero drive denominators required')


def begin(state,c):
    changes={}
    for f in fields(c):
        value=getattr(c,f.name)
        if f.name in ('gear_ratios','gear_losses','inertia_factors','speed_factors'):
            if not 1<=len(value)<=8:raise ValueError('one to eight observed gear table entries required')
            changes[f.name]=tuple(map(f32,value))
        elif f.name not in ('clutch_steps','maximum_rpm','third_enabled','option_kind','secondary_kind'):
            changes[f.name]=f32(value)
    c=replace(c,**changes);s=normalize(state);configuration(c,s)
    return s,c


def update_clutch(state,c):
    """Complete 0x545ec0; +0xb2c engagement and +0xb30 shaped gain."""
    s,c=begin(state,c)
    release=(s.throttle<f32(.01) and s.driven_speed<25) if c.third_enabled else s.override_byte==1
    step=f32(1./c.clutch_steps)
    if release:s.engagement=f32(s.engagement-step)
    elif s.engagement<1:
        if s.bypass or s.damage_one<.5:
            if not c.third_enabled and s.coupling_resistance>200:step=step*f32(.3)
        else:step=f32(step*f32(1.8))
        s.engagement=f32(s.engagement+step)
    s.engagement=max(0.,min(1.,s.engagement))
    if s.engagement in (0.,1.):s.clutch_gain=s.engagement
    else:
        remaining=f32(1.-s.engagement)
        s.clutch_gain=f32(1.-remaining**4)
        if c.third_enabled and s.angular_speed>0:
            fraction=min(1.,f32(s.reference_rotation/s.angular_speed))
            scale=max(1.,min(2.5,f32((1.-fraction)*1.5+1.)))
            s.clutch_gain=f32(scale*s.clutch_gain)
    return s


def prepare_drive(state,c):
    """Complete 0x546130, including reads of previous rotation and speed."""
    s,c=begin(state,c)
    denominator=(s.wheels[3].radius+s.wheels[2].radius)*.5
    if denominator==0:raise ValueError('nonzero mean rear radius required')
    acceleration=f32(max(-100.,min(100.,f32(s.acceleration/denominator))))
    ratio,final=f32(c.gear_ratios[s.gear]),f32(c.final_drive)
    if s.gear!=1 and ratio==0:raise ValueError('nonzero active gear ratio required')
    s.wheel_acceleration=acceleration
    s.output_rotation=f32(s.prior_output_rotation/final)
    s.final_drive_acceleration=f32(acceleration*final)
    s.prior_output_rotation=s.driven_speed if s.gear==1 else f32(s.previous_rotation/ratio)
    s.drag_speed=f32((s.rpm*f32(.10471976)-s.previous_rotation)*32.) if s.engagement<=0 else f32(acceleration*final*ratio)
    s.previous_rotation=f32(s.rpm*f32(.10471976))
    maximum=0.
    for w in s.wheels:
        if w.driven and w.contact:
            maximum=max(maximum,abs(f32(w.spin*final)));s.driven_speed=maximum
    s.reference_rotation=f32((s.angular_speed-s.reference_rotation)*s.engagement+s.reference_rotation) if s.gear==1 else f32(ratio*s.driven_speed)
    # FST writes +0xb3c but retains the unrounded x87 sum for the following
    # product. Using the rounded memory image here changes engine acceleration.
    summed=c.inertia_factors[s.gear]+s.inertia_sum
    s.coupling_resistance=f32((s.angular_speed-s.reference_rotation)*summed*s.engagement*s.engagement*32.)
    return s


def accumulate_drive_request(state,c):
    """Complete 0x546ad0; a condition request accumulator, not clutch setup."""
    s,c=begin(state,c)
    if s.alternate_speed<=2.5:return s
    value=f32(1.0416667e-5 if s.component_mode==5 else 5.2083333e-6 if s.component_mode in (2,3,4,7) else 2.6041666e-6)
    if c.option_one>0 and c.option_two>0:value=f32(value*f32({1:.05,2:.025,3:.0125}.get(c.option_kind,.1)))
    if c.increment_gain>0:value=f32((f32(c.increment_gain)*f32(.02)+1.)*value)
    if c.secondary_gain!=0:
        value=f32((f32(c.secondary_gain)+1.)*value)
        value=f32(value*f32({1:.5,2:.25,3:.125}.get(c.secondary_kind,.75)))
    s.request=max(0.,min(1.,f32(s.request+value)))
    return s


def distribute_drive(state,c,execute):
    """Complete 0x547c60 with mandatory damage/effect consumers."""
    if not callable(execute):raise ValueError('drive effects required')
    s,c=begin(state,c)
    s.transmitted_torque=f32(s.clutch_gain*s.effective_torque) if s.effective_torque>0 or s.engagement>=1 else 0. if s.driven_speed>=25 else 10.
    if s.gear==1:s.output_torque=0.
    elif s.hold_ticks!=0:
        s.output_torque=0.;s.hold_ticks=(s.hold_ticks-1+0x80000000)%0x100000000-0x80000000
    else:
        s.gearbox_drag=f32(abs(s.drag_speed)*f32(c.inertia_factors[s.gear]))
        s.output_torque=f32((s.transmitted_torque-s.gearbox_drag)*f32(c.gear_losses[s.gear])*f32(c.gear_ratios[s.gear]))
    ratio=f32(s.output_torque/f32(c.torque_capacity))
    if ratio>1 and not s.bypass:
        execute(DriveCall('damage',13,(f32((s.output_torque-f32(c.torque_capacity))**2/f32(c.torque_capacity)),)),s)
        execute(DriveCall('effect',25,(f32(abs(s.speed)*min(4.,ratio)*.03125),)),s)
    if not s.bypass:
        for name in ('damage_one','damage_two'):
            damage=getattr(s,name)
            if damage>=.25:
                delta=f32(damage-.25);s.output_torque=f32((1.-delta*delta)*s.output_torque)
    efficiency=f32(c.efficiency)
    if not c.third_enabled and vehicle_control_mode(s.vehicle_flags,s.local_player,s.mode_setting):
        reduced=f32(efficiency-f32(.025))
        if reduced>=efficiency:raise ValueError('original drive-efficiency diagnostic boundary unsupported')
        efficiency=reduced
    for w in s.wheels:
        s.accumulated_drag=f32(abs(s.final_drive_acceleration)*s.inertia_sum)
        w.torque=f32((s.output_torque-s.accumulated_drag)*w.distribution*f32(c.final_drive)*efficiency)
    if c.third_enabled and s.auxiliary_byte:
        s.engine_flags=s.engine_flags|0x20 if s.reference_rotation<0 and s.engagement==0 else s.engine_flags&0xffffffdf
    # This final test overwrites the preceding auxiliary-byte flag decision.
    s.engine_flags=s.engine_flags|0x20 if abs(s.speed)<1 and s.raw_throttle==0 else s.engine_flags&0xffffffdf
    return normalize(s)


def apply_drive_forces(state,c,execute):
    """Complete 0x548050; service gate queried separately for each driven wheel."""
    if not callable(execute):raise ValueError('vehicle gate observation required')
    s,c=begin(state,c)
    for w in s.wheels:
        if not w.driven:
            if s.acceleration>0 and w.contact and w.normal_load!=0:
                w.longitudinal_force=f32(w.longitudinal_force-abs(s.wheel_acceleration)*w.inertia)
            continue
        enabled=False
        if not s.engine_flags&0x20:
            enabled=execute(DriveCall('vehicle_gate'),s)
            if type(enabled) is not bool:raise ValueError('boolean vehicle gate required')
        if enabled:
            s.accumulated_drag=f32(w.inertia*s.wheel_acceleration+s.accumulated_drag)
            if w.radius==0:raise ValueError('nonzero driven wheel radius required')
            force=f32((w.torque-abs(s.wheel_acceleration)*w.inertia)/w.radius)
            if s.gear==0:force=-force
        else:force=0.;w.adjustment=0.;w.spin=0.
        if w.contact and w.normal_load!=0:
            factor=f32(c.speed_factors[s.gear])
            if s.gear==0 and s.rpm*factor*f32(1.05)<abs(s.longitudinal_speed):force=0.
            elif s.gear>1 and s.rpm*factor*f32(1.05)<s.longitudinal_speed:force=0.
            if c.maximum_rpm*factor<abs(s.longitudinal_speed):force=0.
            w.longitudinal_force=f32(w.longitudinal_force+force)
        # This ratio/final-drive product remains on the x87 stack through the
        # division; no float32 memory store occurs before spin adjustment.
        denominator=c.gear_ratios[s.gear]*c.final_drive
        if denominator==0:denominator=1.
        w.adjustment=f32(w.conversion*w.longitudinal_force*w.radius/denominator)
    return normalize(s)
