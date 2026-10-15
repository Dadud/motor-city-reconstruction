"""Recovered 0x540fd0 input smoothing with mandatory external child effects."""
from copy import deepcopy
from dataclasses import dataclass
from client.tire_response import f32


@dataclass
class ControlState:
    target_throttle: int = 0
    target_brake: int = 0
    target_gear: int = 1
    smooth_throttle: bool = True
    smooth_steering: bool = True
    smooth_brake: bool = True
    throttle: int = 0
    brake: int = 0
    output_gear: int = 1
    auxiliary_control: int = 0
    reverse_control: int = 0
    slow_steering: int = 0
    target_steering: int = 0
    steering: int = 0
    emergency: bool = False
    steering_output: float = 0
    brake_output: float = 0
    throttle_output: float = 0
    flags: int = 0
    remote_controls: bool = False
    local_player: bool = False
    steering_setting: int = 128
    throttle_setting: int = 128
    brake_setting: int = 128
    brake_limit: int = 255
    new_steering_mode: bool = True
    steering_return_rate: float = 8
    steering_attack_rate: float = 8
    assisted_gears: bool = False


@dataclass(frozen=True)
class ControlCall:
    stage: str
    values: tuple = ()


@dataclass(frozen=True)
class ControlOutput:
    state: ControlState
    calls: tuple


def _clamp(value, low, high):return max(low,min(high,value))


def _rate(s, value, setting):
    if not s.local_player:return value
    factor=_clamp(f32(setting*.00390625+.5),.5,1.5)
    return max(1,round(f32(factor*value)))


def _normalize(s):
    for name in ('target_throttle','target_brake','target_gear','throttle','brake','output_gear',
                 'auxiliary_control','reverse_control','slow_steering'):
        value=getattr(s,name)
        if type(value) is not int or not 0<=value<=255:raise ValueError('byte control required')
    for name in ('steering_setting','throttle_setting','brake_setting','flags'):
        value=getattr(s,name)
        if type(value) is not int or not 0<=value<=0xffffffff:raise ValueError('unsigned setting/flags required')
    for name in ('target_steering','steering','brake_limit'):
        value=getattr(s,name)
        if type(value) is not int or not -32768<=value<=32767:raise ValueError('bounded signed control observation required')
    for name in ('smooth_throttle','smooth_steering','smooth_brake','emergency','remote_controls','local_player','new_steering_mode','assisted_gears'):
        if type(getattr(s,name)) is not bool:raise ValueError('boolean control flag required')
    for name in ('steering_output','brake_output','throttle_output','steering_return_rate','steering_attack_rate'):
        setattr(s,name,f32(getattr(s,name)))
    if not 0<=s.steering_return_rate<=32767 or not 0<=s.steering_attack_rate<=32767:
        raise ValueError('bounded nonnegative steering rates required')
    return s


def update_controls(state,execute):
    """Execute controls with explicit remote/gear effects and emergency queries.

    execute(call, mutable_state) must implement the requested child operation.
    Query calls return boolean observations. No runtime no-op is supplied.
    """
    if not callable(execute):raise ValueError('child executor required')
    s=_normalize(deepcopy(state));calls=[]
    def call(stage,*values):
        action=ControlCall(stage,values);calls.append(action);result=execute(action,s)
        if stage in ('override_query','stopped_query','vehicle_gate') and type(result) is not bool:
            raise ValueError('boolean external observation required')
        return result
    if s.remote_controls:call('remote_controls')
    down=_rate(s,16,s.throttle_setting);up=_rate(s,8,s.throttle_setting)
    if s.smooth_throttle:
        difference=s.target_throttle-s.throttle
        if difference>=32:s.throttle+=min(up,difference)
        elif difference>1:s.throttle+=min(up//2,difference//2)
        elif difference==1:s.throttle+=1
        elif difference<=-32:s.throttle-=min(down,-difference)
        elif difference<-1:s.throttle-=min(down//2,(-difference)//2)
        elif difference==-1:s.throttle-=1
    else:s.throttle=s.target_throttle
    if s.smooth_brake:
        value=s.target_brake if s.target_brake<=s.brake else s.brake+_rate(s,10,s.brake_setting)
        if s.local_player:value=min(value,_clamp(s.brake_limit,0,255))&255
        s.brake=_clamp(value,0,s.target_brake)
    else:s.brake=s.target_brake
    target,old=s.target_steering,s.steering
    if s.new_steering_mode:
        if not s.smooth_steering:s.steering=target
        else:
            if target==0:
                if old!=0 and s.slow_steering==0:
                    rate=_rate(s,round(s.steering_return_rate),s.steering_setting)
                    s.steering=old+(min(rate,-old) if old<0 else -min(rate,old))
            else:
                difference=target-old;rate=_rate(s,round(s.steering_attack_rate),s.steering_setting)
                if s.slow_steering:rate=2
                s.steering=old+(min(rate,difference) if difference>=0 else -min(rate,-difference))
            s.steering=_clamp(s.steering,-127,127)
    elif s.smooth_steering:
        if (target>0 and old<0) or (target<0 and old>0):s.steering=0
        elif target==0 and old!=0:
            rate=_rate(s,round(s.steering_attack_rate),s.steering_setting)
            s.steering=old+(min(rate,-old) if old<0 else -min(rate,old))
        else:
            difference=target-old;rate=_rate(s,round(s.steering_return_rate),s.steering_setting)
            if difference>=0:
                if old<=32:rate*=2
                elif old>96:rate//=4
                elif old>64:rate//=2
            else:
                if old>=-32:rate*=2
                elif old<-96:rate//=4
                elif old<-64:rate//=2
            s.steering=old+(min(rate,difference) if difference>=0 else -min(rate,-difference))
        s.steering=_clamp(s.steering,-127,127)
    else:s.steering=_clamp(old+_clamp(target-old,-32,32),-127,127)
    call('assisted_gears' if s.assisted_gears else 'manual_gears')
    override=s.emergency or call('stopped_query')
    if override:
        if call('override_query',1):s.target_steering=0;s.steering=0
        else:s.reverse_control=1
        s.throttle=0;s.target_throttle=0;s.auxiliary_control=0
        s.target_gear=1;s.output_gear=1;s.brake=192
    elif not call('vehicle_gate'):s.brake=255
    old_throttle=s.throttle_output
    s.throttle_output=_clamp(f32(s.throttle*f32(1/255)),0.,1.)
    if s.throttle_output<old_throttle:s.flags|=4
    else:s.flags&=0xfffffffb
    # The original byte product remains extended after its FST before the square.
    extended=s.brake*f32(1/255);fraction=f32(extended)
    brake_output=_clamp(f32(extended*fraction*.5+fraction*.5),0.,1.)
    call('trace_controls',fraction,brake_output)
    s.brake_output=brake_output
    s.steering_output=f32(s.steering*f32(1/127))
    return ControlOutput(s,tuple(calls))
