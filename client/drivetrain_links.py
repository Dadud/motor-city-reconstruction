"""Recovered 0x546330/0x5464c0 condition and thermal links.

Temperature-like field names are interpretations, not established units. Damage
and effect consumers require explicit supplied behavior; no wear model is added.
"""
from copy import deepcopy
from dataclasses import dataclass, fields
from client.tire_response import f32

@dataclass
class DrivetrainLinksState:
    engine_flags: int = 1
    vehicle_flags: int = 0
    rpm: int = 3000
    mode: int = 0
    alternate_enabled: bool = False
    bypass: bool = False
    speed: float = 20
    normalized_rpm: float = .4
    engagement: float = .5
    auxiliary_temperature: float = 125
    auxiliary_capacity: float = 10
    condition: float = .9
    main_temperature: float = 100
    loss: float = 0
    drive_scale: float = .1
    primary_drive: float = .01
    alternate_drive: float = .02
    third_temperature: float = 100
    gate_one: float = .1
    gate_two: float = .1
    threshold_observation: float = 0
    request: float = 0
    rate_two: float = 0
    rate_one: float = 0
    shielding_one: float = .2
    shielding_two: float = .2

@dataclass(frozen=True)
class DrivetrainLinksConfig:
    material_index: int = 2
    durability_index: int = 1
    loss_index: int = 1
    third_enabled: bool = True
    mode_coefficients: tuple = (.8,1.,.7)
    alternate_threshold: float = 1
    thermal_gain: float = .01
    cooling_capacity: float = 10
    main_loss_coefficient: float = .01
    transfer_coefficient: float = .1
    reference: float = 100
    upgrade_enabled: float = 0
    upgrade_cooling: float = 0
    upgrade_capacity: float = 0

@dataclass(frozen=True)
class LinkCall:
    stage: str
    code: int
    values: tuple

@dataclass(frozen=True)
class DrivetrainLinksOutput:
    state: DrivetrainLinksState
    calls: tuple

INTS={'engine_flags','vehicle_flags','rpm','mode'}
BOOLS={'alternate_enabled','bypass'}
CONFIG_INTS={'material_index','durability_index','loss_index'}

def normalize(s):
    for n in ('engine_flags','vehicle_flags'):
        if type(getattr(s,n)) is not int or not 0<=getattr(s,n)<=0xffffffff:raise ValueError('uint32 flags required')
    if type(s.rpm) is not int or not -0x80000000<=s.rpm<0x80000000:raise ValueError('signed RPM required')
    if type(s.mode) is not int or not 0<=s.mode<=255:raise ValueError('byte mode required')
    for n in BOOLS:
        if type(getattr(s,n)) is not bool:raise ValueError('boolean observation required')
    for f in fields(s):
        if f.name not in INTS|BOOLS:setattr(s,f.name,f32(getattr(s,f.name)))
    return s

def setup(state,config,execute):
    if not callable(execute):raise ValueError('explicit damage and effect executor required')
    s=normalize(deepcopy(state));values={}
    for f in fields(config):
        v=getattr(config,f.name)
        if f.name in CONFIG_INTS:
            if type(v) is not int or not -0x80000000<=v<0x80000000:raise ValueError('signed config index required')
        elif f.name=='third_enabled':
            if type(v) is not bool:raise ValueError('boolean third-system observation required')
        elif f.name=='mode_coefficients':v=tuple(map(f32,v))
        else:v=f32(v)
        values[f.name]=v
    c=DrivetrainLinksConfig(**values);calls=[]
    def call(stage,code,*values):
        action=LinkCall(stage,code,tuple(map(f32,values)));calls.append(action)
        execute(action,s);normalize(s)
    return s,c,calls,call

def clamp(v,lo=0.,hi=1.):return min(hi,max(lo,v))

def update_gear_link(state,config,execute):
    s,c,calls,call=setup(state,config,execute)
    denominator=c.material_index+4.
    if denominator==0:raise ValueError('singular material index')
    s.gate_one=clamp(f32(f32(4.73175)/denominator*s.rate_one*f32(.00013020834)+s.gate_one))
    if not s.engine_flags&1:s.engagement=0.
    elif 1.-s.gate_one<=f32(.2):s.engagement=0.;call('damage',4,0.)
    else:s.engagement=clamp(f32(s.normalized_rpm*.5+s.auxiliary_temperature*f32(.0017142858)+f32(.3)))
    if s.auxiliary_temperature>200:call('effect_range',23,f32(.0019999999)/s.auxiliary_temperature,0.,1.,.25)
    if s.request>f32(.05):call('damage',5,s.request-f32(.1))
    return DrivetrainLinksOutput(s,tuple(calls))

def update_drivetrain_loads(state,config,execute):
    s,c,calls,call=setup(state,config,execute)
    if s.bypass:
        s.main_temperature=100.;s.auxiliary_temperature=125.;s.condition=min(s.condition,f32(.9))
        return DrivetrainLinksOutput(s,tuple(calls))
    speed=max(1.,abs(s.speed))
    if s.vehicle_flags&0x200:speed=min(speed,20.)
    s.gate_two=clamp(f32(s.rate_two*.03125+s.gate_two))
    reference=c.reference
    if reference==0:raise ValueError('nonzero reference required')
    candidate=f32(reference*s.condition);shield=f32(1.-s.shielding_one)
    drive=s.alternate_drive if s.alternate_enabled and c.alternate_threshold>s.threshold_observation else s.primary_drive
    drive=f32(drive*s.rpm*s.drive_scale*.03125)
    if c.third_enabled:
        if s.mode>=len(c.mode_coefficients):raise ValueError('supplied mode coefficient required')
        capacity=f32(10.415999);cooling=f32(speed*f32(.0001)+f32(.002))
        if c.upgrade_enabled>0:
            capacity=f32(c.upgrade_capacity*f32(.868)+f32(10.415999));cooling=f32(c.upgrade_cooling+cooling)
        if capacity==0:raise ValueError('nonzero third-system capacity required')
        heat=0. if s.mode==1 else (1.-c.mode_coefficients[s.mode]+f32(.02))*drive
        s.third_temperature=min(185.,f32((heat-(s.third_temperature-20.)*clamp(shield,f32(.2))*cooling)/(capacity*f32(1.92))+s.third_temperature))
        if s.third_temperature>130:
            call('damage',15,s.third_temperature*f32(.0076923077))
            call('effect',24,s.third_temperature*f32(.00024038462))
    if s.main_temperature<90:main_loss=0.;s.loss=0.
    else:
        main_loss=f32(-(s.main_temperature-20.)*c.main_loss_coefficient*s.normalized_rpm*shield)
        s.loss=f32((c.loss_index+1.)*4.*s.normalized_rpm)
    remaining=f32(1.-s.gate_two);cool_capacity=f32(remaining*c.cooling_capacity)
    if cool_capacity<=0:transfer=0.;candidate=reference
    else:
        transfer=f32(-(s.main_temperature-candidate)*s.normalized_rpm*c.transfer_coefficient)
        outgoing=0. if s.main_temperature<=90 else -(candidate-20.)*speed*c.transfer_coefficient*f32(.0375)
        net=f32(transfer-outgoing*shield)
        raw_candidate=candidate-net/(cool_capacity*f32(3.74));candidate=f32(raw_candidate)
        if reference<=raw_candidate:
            candidate=min(candidate,reference)
            s.gate_two=clamp(f32(net*f32(.000530504)/cool_capacity+s.gate_two))
    if s.engagement<=0:auxiliary_heat=0.;s.auxiliary_temperature=150.
    else:
        factor=f32(c.material_index*f32(.0001)+f32(.0005))
        auxiliary_heat=-(s.main_temperature-s.auxiliary_temperature)*factor*s.engagement
        outgoing=0. if s.auxiliary_temperature<=120 else -(s.auxiliary_temperature-20.)*factor*speed*.25
        denominator=(1.-s.gate_one)*s.auxiliary_capacity*f32(1.92)
        if denominator==0:raise ValueError('nonzero auxiliary capacity required')
        s.auxiliary_temperature=f32(s.auxiliary_temperature-(auxiliary_heat-outgoing*(1.-s.shielding_two))/denominator)
    s.main_temperature=f32((auxiliary_heat+transfer+main_loss+drive)*c.thermal_gain+s.main_temperature)
    s.condition=min(1.,f32(candidate/reference))
    if s.condition>=1. or remaining==0.:
        if c.durability_index==-1:raise ValueError('singular durability index')
        call('damage',3,0.)
        value=f32(s.condition/(c.durability_index+1.))
        call('effect',18,value);call('effect',22,value)
    threshold=f32(c.durability_index*10.+250.)
    if threshold<s.main_temperature:
        if threshold==0:raise ValueError('nonzero damage threshold required')
        call('damage',3,0.);call('effect',18,s.main_temperature/threshold)
    return DrivetrainLinksOutput(s,tuple(calls))
