#include "mco/control_update.hpp"
#include <algorithm>
#include <cmath>
#include <stdexcept>
namespace mco {
namespace {
double f(double x) {double out=static_cast<float>(x);if(!std::isfinite(out))throw std::invalid_argument("finite float32 controls required");return out;}
template<class T> T clamp(T x,T lo,T hi) {return std::max(lo,std::min(hi,x));}
int nearest(double x) {const double low=std::floor(x),fraction=x-low;return static_cast<int>(fraction<.5?low:fraction>.5?low+1:std::fmod(low,2)==0?low:low+1);}
int rate(const ControlState& s,int value,std::uint32_t setting) {
    if(!s.local_player)return value;
    return std::max(1,nearest(f(clamp(f(setting*.00390625+.5),.5,1.5)*value)));
}
}
ControlOutput update_controls(ControlState s,const ControlExecutor& execute) {
    if(!execute)throw std::invalid_argument("child executor required");
    for(int value:{s.target_throttle,s.target_brake,s.target_gear,s.throttle,s.brake,s.output_gear,s.auxiliary_control,s.reverse_control,s.slow_steering})
        if(value<0 || value>255)throw std::invalid_argument("byte control required");
    for(int value:{s.target_steering,s.steering,s.brake_limit})if(value<-32768 || value>32767)throw std::invalid_argument("bounded signed control required");
    for(double* p:{&s.steering_output,&s.brake_output,&s.throttle_output,&s.steering_return_rate,&s.steering_attack_rate})*p=f(*p);
    if(s.steering_return_rate<0 || s.steering_return_rate>32767 || s.steering_attack_rate<0 || s.steering_attack_rate>32767)
        throw std::invalid_argument("bounded nonnegative steering rates required");
    std::vector<ControlCall> calls;
    auto call=[&](ControlStage stage,std::vector<double> values=std::vector<double>{}) {ControlCall action{stage,values};calls.push_back(action);return execute(action,s);};
    if(s.remote_controls)call(ControlStage::remote_controls);
    const int down=rate(s,16,s.throttle_setting),up=rate(s,8,s.throttle_setting);
    if(s.smooth_throttle) {
        const int d=s.target_throttle-s.throttle;
        if(d>=32)s.throttle+=std::min(up,d);
        else if(d>1)s.throttle+=std::min(up/2,d/2);
        else if(d==1)++s.throttle;
        else if(d<=-32)s.throttle-=std::min(down,-d);
        else if(d<-1)s.throttle-=std::min(down/2,(-d)/2);
        else if(d==-1)--s.throttle;
    } else s.throttle=s.target_throttle;
    if(s.smooth_brake) {
        int value=s.target_brake<=s.brake?s.target_brake:s.brake+rate(s,10,s.brake_setting);
        if(s.local_player)value=std::min(value,clamp(s.brake_limit,0,255))&255;
        s.brake=clamp(value,0,s.target_brake);
    } else s.brake=s.target_brake;
    const int target=s.target_steering,old=s.steering;
    if(s.new_steering_mode) {
        if(!s.smooth_steering)s.steering=target;
        else {
            if(target==0) {
                if(old!=0 && s.slow_steering==0) {const int r=rate(s,nearest(s.steering_return_rate),s.steering_setting);s.steering=old+(old<0?std::min(r,-old):-std::min(r,old));}
            } else {const int d=target-old;int r=rate(s,nearest(s.steering_attack_rate),s.steering_setting);if(s.slow_steering)r=2;s.steering=old+(d>=0?std::min(r,d):-std::min(r,-d));}
            s.steering=clamp(s.steering,-127,127);
        }
    } else if(s.smooth_steering) {
        if((target>0 && old<0) || (target<0 && old>0))s.steering=0;
        else if(target==0 && old!=0) {const int r=rate(s,nearest(s.steering_attack_rate),s.steering_setting);s.steering=old+(old<0?std::min(r,-old):-std::min(r,old));}
        else {
            const int d=target-old;int r=rate(s,nearest(s.steering_return_rate),s.steering_setting);
            if(d>=0) {if(old<=32)r*=2;else if(old>96)r/=4;else if(old>64)r/=2;}
            else {if(old>=-32)r*=2;else if(old<-96)r/=4;else if(old<-64)r/=2;}
            s.steering=old+(d>=0?std::min(r,d):-std::min(r,-d));
        }
        s.steering=clamp(s.steering,-127,127);
    } else s.steering=clamp(old+clamp(target-old,-32,32),-127,127);
    call(s.assisted_gears?ControlStage::assisted_gears:ControlStage::manual_gears);
    const bool override=s.emergency || call(ControlStage::stopped_query);
    if(override) {
        if(call(ControlStage::override_query,{1})) {s.target_steering=0;s.steering=0;}else s.reverse_control=1;
        s.throttle=0;s.target_throttle=0;s.auxiliary_control=0;s.target_gear=1;s.output_gear=1;s.brake=192;
    } else if(!call(ControlStage::vehicle_gate))s.brake=255;
    const double previous=s.throttle_output;
    s.throttle_output=clamp(f(s.throttle*f(1./255)),0.,1.);
    if(s.throttle_output<previous)s.flags|=4;else s.flags&=~std::uint32_t{4};
    const double extended=s.brake*f(1./255),fraction=f(extended);
    const double brake_output=clamp(f(extended*fraction*.5+fraction*.5),0.,1.);
    call(ControlStage::trace_controls,{fraction,brake_output});s.brake_output=brake_output;s.steering_output=f(s.steering*f(1./127));
    return {s,calls};
}
}
