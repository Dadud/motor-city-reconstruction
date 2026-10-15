"""Complete original 0x547120 torque update with explicit producer boundaries."""
from copy import deepcopy
from dataclasses import dataclass, fields, replace
import math
from client.driving_engine_rpm import DrivingEngineRPM, update_driving_engine_rpm
from client.drivetrain_coupling import environment_correction
from client.engine_update import curve_torque_at_rpm, _normalize as normalize_engine, EngineUpdateState
from client.tire_response import f32

@dataclass
class EngineTorqueState:
    rpm_state: DrivingEngineRPM
    engine_flags: int = 1
    bypass: bool = False
    counter: int = 1000
    alternate_enabled: bool = False
    boost_flag: int = 0
    curve_torque: float = 100
    effective_torque: float = 100
    power: float = 0
    engagement: float = .5
    brake_control: float = 0
    condition_accumulator: float = 0
    condition_gate: float = 0
    damage_d3c: float = 0
    damage_d40: float = 0
    damage_d44: float = 0
    damage_d48: float = 0
    damage_d4c: float = 0
    loss: float = 0
    auxiliary_temperature: float = 100
    boost_observation: float = 0
    effect_motion: float = 0
    drag_factor: float = 0
    drag_speed: float = 0
    drag: float = 0
    coupling_resistance: float = 0
    environment_field: float = 0
    environment_override: bool = False
    environment_selector_enabled: bool = False
    environment_selector: int = 0

@dataclass(frozen=True)
class EngineTorqueConfig:
    torque_curve: tuple
    third_enabled: bool = False
    loss_index: int = 1
    material_index: int = 1
    upgrade_enabled: float = 0
    upgrade_index: int = 0
    gain_mode: int = 0
    boost_threshold: float = 1
    boost_available: float = 1
    exhaust_tag: float = 0
    compression: float = 9
    durability_index: int = 3
    limit_a: int = 1
    limit_b: int = 2
    overspeed_base: int = 10000
    overspeed_extra: int = 0
    overload_index: int = 100
    overload_coefficient: float = 10
    torque_capacity: float = 1000

@dataclass(frozen=True)
class TorqueCall:
    stage: str
    code: int | None = None
    values: tuple = ()

@dataclass(frozen=True)
class EngineTorqueOutput:
    state: EngineTorqueState
    calls: tuple

BOOLS={'bypass','alternate_enabled','environment_override','environment_selector_enabled'}
INTS={'engine_flags','counter','boost_flag','environment_selector'}
CONFIG_INTS={'loss_index','material_index','upgrade_index','gain_mode','durability_index','limit_a','limit_b','overspeed_base','overspeed_extra','overload_index'}

def normalize(s):
    for name in BOOLS:
        if type(getattr(s,name)) is not bool:raise ValueError('boolean torque observation required')
    if type(s.engine_flags) is not int or not 0<=s.engine_flags<=0xffffffff:raise ValueError('uint32 engine flags required')
    for name in INTS-{'engine_flags'}:
        if type(getattr(s,name)) is not int or not -0x80000000<=getattr(s,name)<=0x7fffffff:raise ValueError('signed torque observation required')
    for field in fields(s):
        if field.name not in BOOLS|INTS|{'rpm_state'}:setattr(s,field.name,f32(getattr(s,field.name)))
    # Reuse the existing engine storage contract, including enabled-bit ownership.
    container=EngineUpdateState(s.rpm_state,s.engine_flags,0,0,(0,)*8,0,0.,False,0.,())
    s.rpm_state=normalize_engine(container).rpm_state
    if s.rpm_state.idle_rpm<=0:raise ValueError('positive idle RPM required for torque divisions')
    return s

def update_engine_torque(state,config,execute):
    if not callable(execute):raise ValueError('explicit torque producer/effect executor required')
    s=normalize(deepcopy(state));c=config;calls=[]
    for field in fields(c):
        value=getattr(c,field.name)
        if field.name in CONFIG_INTS:
            if type(value) is not int or not -1000000<=value<=1000000:raise ValueError('bounded signed catalogue field required')
        elif field.name=='third_enabled':
            if type(value) is not bool:raise ValueError('boolean third-system observation required')
        elif field.name=='torque_curve':tuple(map(f32,value))
        else:f32(value)
    c=replace(c,**{field.name:f32(getattr(c,field.name)) for field in fields(c) if field.name not in CONFIG_INTS|{'torque_curve','third_enabled'}})
    if c.torque_capacity==0:raise ValueError('nonzero torque capacity required')
    def call(stage,code=None,*values):
        action=TorqueCall(stage,code,tuple(values));calls.append(action)
        result=execute(action,s);normalize(s);return result
    def effect(stage,code,value):call(stage,code,f32(value))
    def pulse(a,b,d):return float(call('pulse',None,f32(s.counter*.015625),f32(a),f32(b),f32(d)))
    r=s.rpm_state;initial_throttle=r.throttle;normalized=f32(r.rpm/r.limiter_rpm)
    s.rpm_state=replace(r,normalized_rpm=normalized)
    if not s.engine_flags&1:
        s.rpm_state=replace(s.rpm_state,rpm=0,angular_speed=0.);s.effective_torque=0.;s.engagement=0.
    elif r.rpm<r.idle_rpm:
        s.rpm_state=replace(s.rpm_state,rpm=r.idle_rpm,angular_speed=f32(r.idle_rpm*f32(.10471976)))
        s.effective_torque=f32(curve_torque_at_rpm(c.torque_curve,r.idle_rpm));s.engagement=f32(s.engagement*.5)
    else:
        curve=curve_torque_at_rpm(c.torque_curve,r.rpm);s.curve_torque=f32(curve)
        if initial_throttle<=0:
            s.effective_torque=-abs(f32(curve*normalized*f32(.18 if c.third_enabled else .35)))
            query=call('brake_query')
            if type(query) is not int or not -0x80000000<=query<=0xffffffff:raise ValueError('32-bit query result required')
            if query&255:s.effective_torque=f32((1.-s.brake_control)*s.effective_torque)
            s.engine_flags &= 0xfffffff7
        else:
            if not s.bypass:
                if s.condition_gate<f32(.25):s.condition_accumulator=0.
                else:
                    load=s.rpm_state.normalized_rpm*s.rpm_state.throttle
                    delta=f32(.005) if load>f32(.6) else f32(.002) if load>f32(.35) else -f32(.001)
                    s.condition_accumulator=min(1.,max(0.,f32(s.condition_accumulator+delta)))
                factor=1.
                if s.condition_accumulator>=1. or s.damage_d44>=f32(.25) or s.damage_d40>=.25:factor=f32(1.-pulse(.5,.02,.25))
                elif s.damage_d4c>=f32(.75):factor=f32(pulse(2.,.02,.9))
                elif s.damage_d3c>=f32(.75):factor=f32(pulse(1.,.02,.5))
                elif s.damage_d48>=1.:factor=f32(pulse(.33,.02,1.))
                factor=min(1.,max(f32(.2),factor))
            else:factor=1.
            s.effective_torque=f32(factor*s.curve_torque)
            loss=f32(s.loss*60000./(s.rpm_state.rpm*f32(6.2831855)))
            upper=f32((c.loss_index+1.)*10.)
            loss=0. if loss<0. else upper if loss>upper else loss
            retained=s.effective_torque-loss;s.effective_torque=f32(retained)
            if s.auxiliary_temperature>120:
                s.effective_torque=f32(retained-(c.material_index+1.)*s.rpm_state.normalized_rpm*1.5*60000./(s.rpm_state.rpm*f32(6.2831855)))
            if c.third_enabled and c.upgrade_enabled>0:
                deduction=(c.upgrade_index+1.)*s.rpm_state.normalized_rpm
                s.effective_torque=f32(s.effective_torque-(deduction+deduction)*60000./(s.rpm_state.rpm*f32(6.2831855)))
            s.effective_torque=max(0.,s.effective_torque)
            # Original CRT __CIpow, x87 base/exponent, complete helpers execute in oracle.
            reduction=f32(math.pow(1.-s.rpm_state.throttle,6.294926643371582)*f32(2.1532740592956543)*math.pow(s.rpm_state.normalized_rpm,.5177839994430542))
            reduction=min(f32(.98),max(0.,reduction))
            s.engine_flags |= 8;s.effective_torque=f32(s.effective_torque-reduction*s.effective_torque)
            if initial_throttle>f32(.3):
                gain=f32(1.03) if c.gain_mode in (2,3,4,5) else 1.
                if c.gain_mode in (3,4) and initial_throttle>f32(.8):gain=f32(1.0609)
                gain=min(f32(1.1),max(1.,gain));s.effective_torque=f32(gain*s.effective_torque);s.curve_torque=f32(gain*s.curve_torque)
            elif s.rpm_state.normalized_rpm<f32(.7):s.engine_flags &= 0xfffffff7
        if s.alternate_enabled and c.boost_threshold>s.boost_observation and c.exhaust_tag==0 and c.boost_available>0 and s.rpm_state.rpm<s.rpm_state.configured_max_rpm-500:
            s.boost_flag=1;torque,increment=call('boost')
            s.boost_observation=f32(f32(increment)+s.boost_observation)
            s.effective_torque=f32(float(torque)+s.effective_torque);s.curve_torque=f32(float(torque)+s.curve_torque)
        elif c.exhaust_tag!=0:
            motion=f32(abs(s.effect_motion)*f32(.003125));gain=f32(max(0.,f32(c.compression-9.))+1.)
            for code in (18,20,21):effect('effect',code,motion)
            effect('effect',17,gain*motion)
            if gain>1:effect('damage',16,gain-1.)
    s.power=max(0.,f32(s.rpm_state.rpm*s.curve_torque*f32(.00010471976)))
    s.drag=f32(s.drag_factor*s.drag_speed)
    calls.append(TorqueCall('environment'))
    correction=environment_correction(s.environment_field,s.environment_override,s.environment_selector_enabled,s.environment_selector)
    retained=correction*s.effective_torque-s.drag;s.effective_torque=f32(retained)
    if s.rpm_state.gear_index==1 or s.engagement==0:acceleration=retained
    elif s.engagement>=1:acceleration=-s.coupling_resistance+min(retained,0.)
    else:acceleration=(1.-s.engagement*s.engagement)*retained-s.coupling_resistance
    s.rpm_state=replace(s.rpm_state,acceleration_input=f32(acceleration),enabled=bool(s.engine_flags&1))
    calls.append(TorqueCall('rpm_update',s.rpm_state.idle_rpm));s.rpm_state=update_driving_engine_rpm(s.rpm_state,s.rpm_state.idle_rpm)
    threshold=(c.durability_index+1)*500.+5500.
    if s.rpm_state.rpm>threshold:
        amount=f32((s.rpm_state.rpm-threshold)**2*f32(8e-8));effect('damage',7,amount)
        for code in (17,18,23,19,20):effect('effect',code,amount)
    limit=call('rpm_limit',None,c.limit_a,c.limit_b)
    if type(limit) is not int or not -0x80000000<=limit<=0x7fffffff:raise ValueError('signed RPM limit result required')
    if s.rpm_state.rpm>limit:effect('damage',9,(s.rpm_state.rpm-limit)*f32(8e-8))
    threshold=c.overspeed_base+250+c.overspeed_extra
    if s.rpm_state.rpm>threshold:effect('damage',14,(s.rpm_state.rpm-threshold)**2*f32(8e-8))
    threshold=f32(c.overload_index*c.overload_coefficient)
    if s.curve_torque>threshold and not s.bypass:
        amount=(s.curve_torque-threshold)*f32(.05);effect('damage',8,amount*amount*f32(5.2083333e-6))
    ratio=s.curve_torque/c.torque_capacity
    if ratio>1 and not s.bypass:
        ratio=min(5.,f32(ratio));effect('damage',12,ratio*ratio+ratio*ratio)
        effect('effect',24,abs(s.effect_motion)*ratio*.03125)
    return EngineTorqueOutput(s,tuple(calls))
