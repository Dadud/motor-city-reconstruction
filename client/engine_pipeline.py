"""Shared-owner engine dispatcher, torque and condition pipeline.

This connects recovered consumers, not the unknown setup, clutch, wheel-drive,
boost, damage or presentation producers. Every remaining child is explicit.
"""
from copy import deepcopy
from dataclasses import dataclass, fields, replace
from client.engine_update import EngineUpdateState, update_engine, _normalize as normalize_dispatch
from client.engine_torque_update import EngineTorqueState, EngineTorqueConfig, update_engine_torque, normalize as normalize_torque
from client.drivetrain_links import DrivetrainLinksState, DrivetrainLinksConfig, update_gear_link, update_drivetrain_loads
from client.tire_response import f32

@dataclass
class EnginePipelineState(EngineTorqueState):
    vehicle_flags: int = 4
    selector_index: int = 0
    activation_delays: tuple = (32,16,64,48,12,50,40,24)
    override_value: float = 0
    control_gate: bool = False
    motion_metric: float = 0
    # +0xac8, distinct from inherited engagement at +0xb2c.
    thermal_engagement: float = .5
    thermal_mode: int = 0
    auxiliary_capacity: float = 10
    condition: float = .9
    main_temperature: float = 100
    drive_scale: float = .1
    primary_drive: float = .01
    alternate_drive: float = .02
    third_temperature: float = 100
    gate_one: float = .1
    gate_two: float = .1
    request: float = 0
    rate_two: float = 0
    rate_one: float = 0
    shielding_one: float = .2
    shielding_two: float = .2

@dataclass(frozen=True)
class EnginePipelineConfig:
    torque: EngineTorqueConfig
    links: DrivetrainLinksConfig

@dataclass(frozen=True)
class PipelineCall:
    domain: str
    stage: str
    code: int | None = None
    values: tuple = ()

@dataclass(frozen=True)
class EnginePipelineOutput:
    state: EnginePipelineState
    calls: tuple

TORQUE_FIELDS=tuple(f.name for f in fields(EngineTorqueState))
DISPATCH_DIRECT=('rpm_state','engine_flags','vehicle_flags','selector_index','activation_delays',
                 'override_value','control_gate','motion_metric','effective_torque','curve_torque','power','engagement')
LINK_FIELDS=tuple(f.name for f in fields(DrivetrainLinksState))
LINK_ALIASES={'engagement':'thermal_engagement','mode':'thermal_mode',
              'threshold_observation':'boost_observation'}
LINK_RPM={'rpm':'rpm','normalized_rpm':'normalized_rpm','speed':'longitudinal_speed'}

def _torque(s):return EngineTorqueState(**{n:getattr(s,n) for n in TORQUE_FIELDS})
def _import_torque(t,s):
    for n in TORQUE_FIELDS:setattr(s,n,getattr(t,n))

def _dispatch(s,c):
    return EngineUpdateState(**{n:getattr(s,n) for n in DISPATCH_DIRECT},
                             current_counter=s.counter,torque_curve=c.torque.torque_curve)

def _import_dispatch(d,s):
    for n in DISPATCH_DIRECT:setattr(s,n,getattr(d,n))
    s.counter=d.current_counter

def _links(s):
    values={}
    for n in LINK_FIELDS:
        values[n]=getattr(s.rpm_state,LINK_RPM[n]) if n in LINK_RPM else getattr(s,LINK_ALIASES.get(n,n))
    return DrivetrainLinksState(**values)

def _import_links(t,s):
    rpm={}
    for n in LINK_FIELDS:
        if n in LINK_RPM:rpm[LINK_RPM[n]]=getattr(t,n)
        else:setattr(s,LINK_ALIASES.get(n,n),getattr(t,n))
    s.rpm_state=replace(s.rpm_state,**rpm)

def _copy_into(source,target):
    for f in fields(source):setattr(target,f.name,getattr(source,f.name))

def _normalize(s,c):
    _import_torque(normalize_torque(_torque(s)),s)
    _import_dispatch(normalize_dispatch(_dispatch(s,c)),s)
    # All link numeric storage follows the same binary32 contract.
    from client.drivetrain_links import normalize
    _import_links(normalize(_links(s)),s)
    return s

def _validate_config(c):
    pairs=(('material_index','material_index'),('durability_index','durability_index'),
           ('loss_index','loss_index'),('third_enabled','third_enabled'),
           ('upgrade_enabled','upgrade_enabled'),('boost_threshold','alternate_threshold'))
    for torque_name,link_name in pairs:
        a,b=getattr(c.torque,torque_name),getattr(c.links,link_name)
        if (f32(a) if isinstance(a,float) else a)!=(f32(b) if isinstance(b,float) else b):
            raise ValueError('inconsistent shared catalogue field: '+torque_name)

def update_engine_pipeline(state,config,execute):
    """One 0x545af0 invocation with three recovered child bodies connected.

    execute receives PipelineCall plus the canonical mutable owner state. It must
    supply every other child/query. Nested callback writes are synchronized before
    the recovered parent resumes; unknown behavior is never silently installed.
    """
    if not callable(execute):raise ValueError('explicit engine pipeline executor required')
    c=config;_validate_config(c);s=_normalize(deepcopy(state),c);nested=[]
    def external(action):
        result=execute(action,s);_normalize(s,c);return result
    def dispatch_child(action,d):
        _import_dispatch(d,s)
        child_calls=[];nested.append(child_calls)
        if action.stage=='torque_update':
            def torque_child(child,t):
                _import_torque(t,s)
                result=external(PipelineCall('torque_update',child.stage,child.code,child.values))
                _copy_into(_torque(s),t);return result
            out=update_engine_torque(_torque(s),c.torque,torque_child)
            _import_torque(out.state,s)
            child_calls.extend(PipelineCall('torque_update',a.stage,a.code,a.values) for a in out.calls)
        elif action.stage in ('gear_link','drivetrain_loads'):
            def link_child(child,t):
                _import_links(t,s)
                result=external(PipelineCall(action.stage,child.stage,child.code,child.values))
                _copy_into(_links(s),t);return result
            method=update_gear_link if action.stage=='gear_link' else update_drivetrain_loads
            out=method(_links(s),c.links,link_child);_import_links(out.state,s)
            child_calls.extend(PipelineCall(action.stage,a.stage,a.code,a.values) for a in out.calls)
        else:
            result=external(PipelineCall('dispatch',action.stage,action.argument))
            _copy_into(_dispatch(s,c),d);return result
        _normalize(s,c);_copy_into(_dispatch(s,c),d)
    out=update_engine(_dispatch(s,c),dispatch_child);_import_dispatch(out.state,s)
    calls=[];index=0
    for action in out.calls:
        calls.append(PipelineCall('dispatch',action.stage,action.argument))
        if action.stage not in ('rpm_update','curve_lookup'):
            calls.extend(nested[index]);index+=1
    return EnginePipelineOutput(_normalize(s,c),tuple(calls))
