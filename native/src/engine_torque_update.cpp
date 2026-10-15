#include "mco/engine_torque_update.hpp"
#include "mco/engine_update.hpp"
#include "mco/drivetrain_coupling.hpp"
#include <algorithm>
#include <cmath>
#include <limits>
#include <stdexcept>
#include <utility>
namespace mco {namespace {
float f(double v){if(!std::isfinite(v)||std::abs(v)>std::numeric_limits<float>::max())throw std::invalid_argument("finite torque value required");return static_cast<float>(v);}
double d(float v){return double(v);}
void normalize(EngineTorqueState&s){
 auto&r=s.rpm_state;r.enabled=(s.engine_flags&1)!=0;
 if(r.idle_rpm<=0||r.limiter_rpm<=0)throw std::invalid_argument("positive idle and limiter required");
 for(auto v:{r.idle_rpm,r.configured_max_rpm,r.target_rpm,r.rpm,r.limiter_rpm,r.gear_index})if(v==std::numeric_limits<std::int32_t>::min())throw std::invalid_argument("bounded RPM field required");
 for(auto v:{r.throttle,r.normalized_rpm,r.inertia_factor,r.acceleration_input,r.angular_speed,r.gear_speed_factor,r.longitudinal_speed,r.acceleration_output,s.curve_torque,s.effective_torque,s.power,s.engagement,s.brake_control,s.condition_accumulator,s.condition_gate,s.damage_d3c,s.damage_d40,s.damage_d44,s.damage_d48,s.damage_d4c,s.loss,s.auxiliary_temperature,s.boost_observation,s.effect_motion,s.drag_factor,s.drag_speed,s.drag,s.coupling_resistance,s.environment_field})f(v);
}
}
EngineTorqueOutput update_engine_torque(EngineTorqueState s,const EngineTorqueConfig&c,const TorqueStageExecutor&execute){
 if(!execute)throw std::invalid_argument("explicit torque producer/effect executor required");
 normalize(s);std::vector<TorqueCall>calls;
 for(auto v:{c.loss_index,c.material_index,c.upgrade_index,c.gain_mode,c.durability_index,c.limit_a,c.limit_b,c.overspeed_base,c.overspeed_extra,c.overload_index})if(v < -1000000||v>1000000)throw std::invalid_argument("bounded catalogue field required");
 for(auto v:{c.upgrade_enabled,c.boost_threshold,c.boost_available,c.exhaust_tag,c.compression,c.overload_coefficient,c.torque_capacity})f(v);
 for(auto v:c.torque_curve)f(v);
 if(c.torque_capacity==0)throw std::invalid_argument("nonzero torque capacity required");
 auto call=[&](const char*stage,std::optional<std::int32_t>code={},std::vector<double>values={}){
  TorqueCall action{stage,code,std::move(values)};calls.push_back(action);auto result=execute(action,s);normalize(s);
  if(!std::isfinite(result.value))throw std::invalid_argument("finite torque child result required");
  return result;
 };
 auto effect=[&](const char*stage,int code,double value){call(stage,code,{d(f(value))});};
 auto pulse=[&](double a,double b,double v){return call("pulse",{},{d(f(double(s.counter)*.015625)),d(f(a)),d(f(b)),d(f(v))}).value;};
 const auto incoming=s.rpm_state;const float initial_throttle=incoming.throttle;
 const float normalized=f(double(incoming.rpm)/incoming.limiter_rpm);s.rpm_state.normalized_rpm=normalized;
 if(!(s.engine_flags&1)){s.rpm_state.rpm=0;s.rpm_state.angular_speed=0;s.effective_torque=0;s.engagement=0;}
 else if(incoming.rpm<incoming.idle_rpm){
  s.rpm_state.rpm=incoming.idle_rpm;s.rpm_state.angular_speed=f(double(incoming.idle_rpm)*d(f(.10471976)));
  s.effective_torque=f(curve_torque_at_rpm(c.torque_curve,incoming.idle_rpm));s.engagement=f(d(s.engagement)*.5);
 }else{
  double curve=curve_torque_at_rpm(c.torque_curve,incoming.rpm);s.curve_torque=f(curve);
  if(initial_throttle<=0){
   s.effective_torque=-std::abs(f(curve*normalized*d(f(c.third_enabled?.18:.35))));
   double query=call("brake_query").value;
   if(std::floor(query)!=query||query < -2147483648.||query>4294967295.)throw std::invalid_argument("32-bit query result required");
   if(static_cast<std::int64_t>(query)&255)s.effective_torque=f((1.-s.brake_control)*s.effective_torque);
   s.engine_flags&=0xfffffff7;
  }else{
   double factor=1;
   if(!s.bypass){
    if(s.condition_gate<f(.25))s.condition_accumulator=0;
    else{double load=d(s.rpm_state.normalized_rpm)*s.rpm_state.throttle;float delta=load>d(f(.6))?f(.005):load>d(f(.35))?f(.002):-f(.001);s.condition_accumulator=std::clamp(f(d(s.condition_accumulator)+delta),0.f,1.f);}
    if(s.condition_accumulator>=1||s.damage_d44>=f(.25)||s.damage_d40>=.25)factor=f(1.-pulse(.5,.02,.25));
    else if(s.damage_d4c>=f(.75))factor=f(pulse(2,.02,.9));
    else if(s.damage_d3c>=f(.75))factor=f(pulse(1,.02,.5));
    else if(s.damage_d48>=1)factor=f(pulse(.33,.02,1));
    factor=std::clamp(factor,d(f(.2)),1.);
   }
   s.effective_torque=f(factor*s.curve_torque);
   float loss=f(d(s.loss)*60000./(double(s.rpm_state.rpm)*d(f(6.2831855))));
   float upper=f((double(c.loss_index)+1)*10);loss=loss<0?0:loss>upper?upper:loss;
   double retained=d(s.effective_torque)-loss;s.effective_torque=f(retained);
   if(s.auxiliary_temperature>120)s.effective_torque=f(retained-(double(c.material_index)+1)*s.rpm_state.normalized_rpm*1.5*60000./(double(s.rpm_state.rpm)*d(f(6.2831855))));
   if(c.third_enabled&&c.upgrade_enabled>0){double deduction=(double(c.upgrade_index)+1)*s.rpm_state.normalized_rpm;s.effective_torque=f(d(s.effective_torque)-(deduction+deduction)*60000./(double(s.rpm_state.rpm)*d(f(6.2831855))));}
   s.effective_torque=std::max(0.f,s.effective_torque);
   float reduction=f(std::pow(1.-s.rpm_state.throttle,6.294926643371582)*d(f(2.1532740592956543))*std::pow(d(s.rpm_state.normalized_rpm),.5177839994430542));
   reduction=std::clamp(reduction,0.f,f(.98));s.engine_flags|=8;s.effective_torque=f(d(s.effective_torque)-d(reduction)*s.effective_torque);
   if(initial_throttle>f(.3)){
    float gain=c.gain_mode>=2&&c.gain_mode<=5?f(1.03):1;
    if((c.gain_mode==3||c.gain_mode==4)&&initial_throttle>f(.8))gain=f(1.0609);
    gain=std::clamp(gain,1.f,f(1.1));s.effective_torque=f(d(gain)*s.effective_torque);s.curve_torque=f(d(gain)*s.curve_torque);
   }else if(s.rpm_state.normalized_rpm<f(.7))s.engine_flags&=0xfffffff7;
  }
  if(s.alternate_enabled&&c.boost_threshold>s.boost_observation&&c.exhaust_tag==0&&c.boost_available>0&&s.rpm_state.rpm<s.rpm_state.configured_max_rpm-500){
   s.boost_flag=1;auto result=call("boost");s.boost_observation=f(d(result.boost_increment)+s.boost_observation);
   s.effective_torque=f(result.value+s.effective_torque);s.curve_torque=f(result.value+s.curve_torque);
  }else if(c.exhaust_tag!=0){
   float motion=f(std::abs(d(s.effect_motion))*d(f(.003125))),gain=f(d(std::max(0.f,f(d(c.compression)-9)))+1);
   for(int code:{18,20,21})effect("effect",code,motion);
   effect("effect",17,d(gain)*motion);if(gain>1)effect("damage",16,d(gain)-1);
  }
 }
 s.power=std::max(0.f,f(double(s.rpm_state.rpm)*s.curve_torque*d(f(.00010471976))));s.drag=f(d(s.drag_factor)*s.drag_speed);
 calls.push_back({"environment",{}, {}});
 float correction=environment_correction(s.environment_field,s.environment_override,s.environment_selector_enabled,s.environment_selector);
 double retained=d(correction)*s.effective_torque-s.drag;s.effective_torque=f(retained);double acceleration;
 if(s.rpm_state.gear_index==1||s.engagement==0)acceleration=retained;
 else if(s.engagement>=1)acceleration=-d(s.coupling_resistance)+std::min(retained,0.);
 else acceleration=(1.-d(s.engagement)*s.engagement)*retained-s.coupling_resistance;
 s.rpm_state.acceleration_input=f(acceleration);s.rpm_state.enabled=(s.engine_flags&1)!=0;
 calls.push_back({"rpm_update",s.rpm_state.idle_rpm,{}});s.rpm_state=update_driving_engine_rpm(s.rpm_state,s.rpm_state.idle_rpm);
 double threshold=(double(c.durability_index)+1)*500+5500;
 if(s.rpm_state.rpm>threshold){double delta=double(s.rpm_state.rpm)-threshold;float amount=f(delta*delta*d(f(8e-8)));effect("damage",7,amount);for(int code:{17,18,23,19,20})effect("effect",code,amount);}
 double limit=call("rpm_limit",{},{double(c.limit_a),double(c.limit_b)}).value;
 if(!std::isfinite(limit)||std::floor(limit)!=limit||limit < -2147483648.||limit>2147483647.)throw std::invalid_argument("signed RPM limit result required");
 if(s.rpm_state.rpm>limit)effect("damage",9,(double(s.rpm_state.rpm)-limit)*d(f(8e-8)));
 threshold=double(c.overspeed_base)+250+c.overspeed_extra;
 if(s.rpm_state.rpm>threshold){double delta=double(s.rpm_state.rpm)-threshold;effect("damage",14,delta*delta*d(f(8e-8)));}
 threshold=f(double(c.overload_index)*c.overload_coefficient);
 if(s.curve_torque>threshold&&!s.bypass){double amount=(s.curve_torque-threshold)*d(f(.05));effect("damage",8,amount*amount*d(f(5.2083333e-6)));}
 double ratio=d(s.curve_torque)/c.torque_capacity;
 if(ratio>1&&!s.bypass){ratio=std::min(5.,d(f(ratio)));effect("damage",12,ratio*ratio+ratio*ratio);effect("effect",24,std::abs(d(s.effect_motion))*ratio*.03125);}
 return{s,std::move(calls)};
}
}
