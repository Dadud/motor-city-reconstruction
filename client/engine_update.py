"""Original driving-engine dispatcher with recovered RPM and curve consumers.

Other child stages remain mandatory supplied behavior. No prototype torque or
clutch model is silently installed behind these controller decisions.
"""
from copy import deepcopy
from dataclasses import dataclass, replace
import math
from client.driving_engine_rpm import DrivingEngineRPM, update_driving_engine_rpm
from client.tire_response import f32


@dataclass
class EngineUpdateState:
    rpm_state: DrivingEngineRPM
    engine_flags: int
    vehicle_flags: int
    selector_index: int
    activation_delays: tuple
    current_counter: int
    override_value: float
    control_gate: bool
    motion_metric: float
    torque_curve: tuple
    effective_torque: float = 0
    curve_torque: float = 0
    power: float = 0
    engagement: float = 0


@dataclass(frozen=True)
class EngineCall:
    stage: str
    argument: int | None = None


@dataclass(frozen=True)
class EngineUpdateOutput:
    state: EngineUpdateState
    calls: tuple


def signed_counter(value):
    """Original wrapping signed 32-bit arithmetic, separate from float fields."""
    value &= 0xffffffff
    return value-0x100000000 if value&0x80000000 else value


def curve_torque_at_rpm(table,rpm):
    """Original 0x548f00, returning the unstored interpolation intermediate."""
    if type(rpm) is not int or not 0<=rpm<=0x7fffffff:
        raise ValueError('nonnegative signed RPM required')
    if len(table)<2:raise ValueError('at least two torque knots required')
    values=tuple(map(f32,table))
    index=math.floor(rpm*f32(.002))
    if not 0<=index<len(values)-1:
        raise ValueError('RPM outside supplied adjacent torque knots')
    return (values[index+1]-values[index])*(f32(rpm)-index*500)*f32(.002)+values[index]


def _normalize(s):
    for value in (s.engine_flags,s.vehicle_flags):
        if type(value) is not int or not 0<=value<=0xffffffff:raise ValueError('uint32 flags required')
    if type(s.selector_index) is not int or not 0<=s.selector_index<8 or len(s.activation_delays)!=8:
        raise ValueError('supported selector index and eight supplied delays required')
    for value in (*s.activation_delays,s.current_counter):
        if type(value) is not int or not -0x80000000<=value<=0x7fffffff:raise ValueError('signed counter required')
    if type(s.control_gate) is not bool:raise ValueError('boolean control observation required')
    for name in ('override_value','motion_metric','effective_torque','curve_torque','power','engagement'):
        setattr(s,name,f32(getattr(s,name)))
    r=s.rpm_state
    if r.limiter_rpm<=0:raise ValueError('positive limiter required')
    for name in ('idle_rpm','configured_max_rpm','target_rpm','rpm','limiter_rpm','gear_index'):
        value=getattr(r,name)
        if type(value) is not int or not -0x80000000<value<0x80000000:raise ValueError('bounded signed RPM fields required')
    changes={name:f32(getattr(r,name)) for name in ('throttle','normalized_rpm','inertia_factor',
        'acceleration_input','angular_speed','gear_speed_factor','longitudinal_speed','acceleration_output')}
    s.rpm_state=replace(r,enabled=bool(s.engine_flags&1),**changes)
    s.torque_curve=tuple(map(f32,s.torque_curve))
    return s


def _update_engine(state,execute,*,vehicle_system):
    """Shared body for the two observed engine dispatch entry points.

    Recovered rpm_update and curve_lookup are executed internally. execute is
    required for other stages and query observations, with mutable typed state.
    Child state writes round to their original binary32 storage boundaries.
    """
    if not callable(execute):raise ValueError('engine child executor required')
    s=_normalize(deepcopy(state));calls=[]
    def call(stage,argument=None):
        action=EngineCall(stage,argument);calls.append(action)
        result=execute(action,s);_normalize(s)
        return result
    def rpm_update():
        calls.append(EngineCall('rpm_update',s.rpm_state.idle_rpm))
        s.rpm_state=update_driving_engine_rpm(s.rpm_state,s.rpm_state.idle_rpm)
    def fixed_rpm():
        r=s.rpm_state
        rpm=round(f32(r.limiter_rpm*.875))
        s.rpm_state=replace(r,rpm=rpm,angular_speed=f32(rpm*f32(.10471976)),acceleration_output=0.)
    if vehicle_system:
        call('control_update')
        s.engagement=f32(min(s.engagement,f32(.25)))
    if not s.engine_flags&1:
        if call('interface_query',8)==0:
            s.engine_flags|=1;_normalize(s)
        elif signed_counter(call('activation_counter')-256+s.activation_delays[s.selector_index])<=s.current_counter:
            s.engine_flags|=1;_normalize(s);call('enable_signal',1)
    flags=s.vehicle_flags
    if not flags&2:
        if flags&4 and s.engine_flags&1:
            for stage in ('engine_setup','engine_control','gear_link','drivetrain_loads',
                          'engagement_inputs'):
                call(stage)
            if vehicle_system:call('empty_engine_hook')
            for stage in ('torque_update','wheel_drive','engine_finalize'):call(stage)
        return EngineUpdateOutput(s,tuple(calls))
    if not flags&4:
        if not flags&1 or s.override_value==0 or not s.engine_flags&1:
            if not flags&1 or call('start_counter')<=s.current_counter:
                if not s.control_gate and s.motion_metric<f32(11.17575):
                    fraction=f32((.7,.6,.75,.65,.55,.8,.5,.67)[s.selector_index])
                    r=s.rpm_state
                    s.rpm_state=replace(r,acceleration_input=f32(r.limiter_rpm*fraction-r.rpm),
                        throttle=max(.5,min(1.,f32(fraction*f32(1.1)))))
                    rpm_update()
                else:call('idle_regulation')
            else:
                threshold=128 if call('interface_query',1)!=0 else 10
                call('start_acceleration')
                if s.current_counter<=threshold:s.rpm_state=replace(s.rpm_state,acceleration_input=0.)
                if not s.engine_flags&1:
                    s.rpm_state=replace(s.rpm_state,rpm=0,angular_speed=0.)
                    s.effective_torque=0.;s.engagement=0.
                else:rpm_update()
        else:fixed_rpm()
    else:
        if not s.engine_flags&1:s.rpm_state=replace(s.rpm_state,rpm=0,acceleration_input=0.)
        if s.override_value==0 or not s.engine_flags&1:call('torque_update')
        else:fixed_rpm()
    r=s.rpm_state
    s.effective_torque=100.
    s.rpm_state=replace(r,normalized_rpm=f32(r.rpm/r.limiter_rpm))
    calls.append(EngineCall('curve_lookup',r.rpm))
    torque=curve_torque_at_rpm(s.torque_curve,r.rpm)
    s.curve_torque=f32(torque)
    s.power=max(0.,f32(torque*r.rpm*f32(.00010471976)))
    if s.vehicle_flags&1 and s.vehicle_flags&2:
        call('gear_link');call('drivetrain_loads')
    return EngineUpdateOutput(s,tuple(calls))


def update_engine(state,execute):
    """Recover the original 0x545af0 engine dispatcher."""
    return _update_engine(state,execute,vehicle_system=False)


def update_engine_system(state,execute):
    """Recover 0x548260, the vehicle-path engine controller.

    This entry applies the recovered control update and engagement cap before
    sharing the common engine dispatch. Its 0x548660 RET is preserved as an
    ordered call for exact caller comparisons.
    """
    return _update_engine(state,execute,vehicle_system=True)
