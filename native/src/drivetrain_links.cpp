#include "mco/drivetrain_links.hpp"
#include <algorithm>
#include <cmath>
#include <limits>
#include <stdexcept>
#include <utility>
namespace mco { namespace {
float f(double v){if(!std::isfinite(v)||std::abs(v)>std::numeric_limits<float>::max())throw std::invalid_argument("finite condition value required");return static_cast<float>(v);}
double d(float v){return double(v);}
float clamp(float v,float lo=0,float hi=1){return std::clamp(v,lo,hi);}
void normalize(DrivetrainLinksState &s){
 if(s.mode<0||s.mode>255)throw std::invalid_argument("byte mode required");
 for(auto v:{s.speed,s.normalized_rpm,s.engagement,s.auxiliary_temperature,s.auxiliary_capacity,s.condition,s.main_temperature,s.loss,s.drive_scale,s.primary_drive,s.alternate_drive,s.third_temperature,s.gate_one,s.gate_two,s.threshold_observation,s.request,s.rate_two,s.rate_one,s.shielding_one,s.shielding_two})f(v);
}
void validate(const DrivetrainLinksConfig &c,const LinkEffectExecutor &execute){
 if(!execute)throw std::invalid_argument("explicit damage/effect executor required");
 for(auto v:{c.alternate_threshold,c.thermal_gain,c.cooling_capacity,c.main_loss_coefficient,c.transfer_coefficient,c.reference,c.upgrade_enabled,c.upgrade_cooling,c.upgrade_capacity})f(v);
 for(auto v:c.mode_coefficients)f(v);
}
void call(std::vector<LinkCall>&calls,DrivetrainLinksState&s,const LinkEffectExecutor&e,const char*stage,int code,std::vector<float> values){
 LinkCall action{stage,code,std::move(values)};calls.push_back(action);e(action,s);normalize(s);
}
}
DrivetrainLinksOutput update_gear_link(DrivetrainLinksState s,const DrivetrainLinksConfig &c,const LinkEffectExecutor &e){
 validate(c,e);normalize(s);std::vector<LinkCall>calls;
 double denominator=double(c.material_index)+4.;if(denominator==0)throw std::invalid_argument("singular material index");
 s.gate_one=clamp(f(d(f(4.73175))/denominator*s.rate_one*d(f(.00013020834))+s.gate_one));
 if(!(s.engine_flags&1))s.engagement=0;
 else if(1.-s.gate_one<=d(f(.2))){s.engagement=0;call(calls,s,e,"damage",4,{0});}
 else s.engagement=clamp(f(d(s.normalized_rpm)*.5+d(s.auxiliary_temperature)*d(f(.0017142858))+d(f(.3))));
 if(s.auxiliary_temperature>200)call(calls,s,e,"effect_range",23,{f(d(f(.0019999999))/s.auxiliary_temperature),0,1,.25f});
 if(s.request>f(.05))call(calls,s,e,"damage",5,{f(d(s.request)-d(f(.1)))});
 return {s,std::move(calls)};
}
DrivetrainLinksOutput update_drivetrain_loads(DrivetrainLinksState s,const DrivetrainLinksConfig &c,const LinkEffectExecutor &e){
 validate(c,e);normalize(s);std::vector<LinkCall>calls;
 if(s.bypass){s.main_temperature=100;s.auxiliary_temperature=125;s.condition=std::min(s.condition,f(.9));return{s,std::move(calls)};}
 double speed=std::max(1.,std::abs(d(s.speed)));if(s.vehicle_flags&0x200)speed=std::min(speed,20.);
 s.gate_two=clamp(f(d(s.rate_two)*.03125+s.gate_two));double reference=c.reference;
 if(reference==0)throw std::invalid_argument("nonzero reference required");
 float candidate=f(reference*s.condition),shield=f(1.-s.shielding_one);
 float drive=s.alternate_enabled&&c.alternate_threshold>s.threshold_observation?s.alternate_drive:s.primary_drive;
 drive=f(d(drive)*s.rpm*s.drive_scale*.03125);
 if(c.third_enabled){
  if(std::size_t(s.mode)>=c.mode_coefficients.size())throw std::invalid_argument("supplied mode coefficient required");
  float capacity=f(10.415999),cooling=f(speed*d(f(.0001))+d(f(.002)));
  if(c.upgrade_enabled>0){capacity=f(d(c.upgrade_capacity)*d(f(.868))+d(f(10.415999)));cooling=f(d(c.upgrade_cooling)+cooling);}
  if(capacity==0)throw std::invalid_argument("nonzero third capacity required");
  double heat=s.mode==1?0:(1.-c.mode_coefficients[s.mode]+d(f(.02)))*drive;
  s.third_temperature=std::min(185.f,f((heat-(d(s.third_temperature)-20.)*clamp(shield,f(.2))*cooling)/(d(capacity)*d(f(1.92)))+s.third_temperature));
  if(s.third_temperature>130){call(calls,s,e,"damage",15,{f(d(s.third_temperature)*d(f(.0076923077)))});call(calls,s,e,"effect",24,{f(d(s.third_temperature)*d(f(.00024038462)))});}
 }
 float main_loss;
 if(s.main_temperature<90){main_loss=0;s.loss=0;}
 else{main_loss=f(-(d(s.main_temperature)-20.)*c.main_loss_coefficient*s.normalized_rpm*shield);s.loss=f((double(c.loss_index)+1.)*4.*s.normalized_rpm);}
 float remaining=f(1.-s.gate_two),cool_capacity=f(d(remaining)*c.cooling_capacity),transfer;
 if(cool_capacity<=0){transfer=0;candidate=f(reference);}
 else{
  transfer=f(-(d(s.main_temperature)-candidate)*s.normalized_rpm*c.transfer_coefficient);
  double outgoing=s.main_temperature<=90?0:-(d(candidate)-20.)*speed*c.transfer_coefficient*d(f(.0375));
  float net=f(d(transfer)-outgoing*shield);double raw_candidate=d(candidate)-d(net)/(d(cool_capacity)*d(f(3.74)));candidate=f(raw_candidate);
  if(reference<=raw_candidate){candidate=std::min(candidate,f(reference));s.gate_two=clamp(f(d(net)*d(f(.000530504))/cool_capacity+s.gate_two));}
 }
 double auxiliary_heat;
 if(s.engagement<=0){auxiliary_heat=0;s.auxiliary_temperature=150;}
 else{
  float factor=f(double(c.material_index)*d(f(.0001))+d(f(.0005)));
  auxiliary_heat=-(d(s.main_temperature)-s.auxiliary_temperature)*factor*s.engagement;
  double outgoing=s.auxiliary_temperature<=120?0:-(d(s.auxiliary_temperature)-20.)*factor*speed*.25;
  double denominator=(1.-s.gate_one)*s.auxiliary_capacity*d(f(1.92));if(denominator==0)throw std::invalid_argument("nonzero auxiliary capacity required");
  s.auxiliary_temperature=f(d(s.auxiliary_temperature)-(auxiliary_heat-outgoing*(1.-s.shielding_two))/denominator);
 }
 s.main_temperature=f((auxiliary_heat+transfer+main_loss+drive)*c.thermal_gain+s.main_temperature);
 s.condition=std::min(1.f,f(d(candidate)/reference));
 if(s.condition>=1||remaining==0){
  if(c.durability_index==-1)throw std::invalid_argument("singular durability index");
  call(calls,s,e,"damage",3,{0});float value=f(d(s.condition)/(double(c.durability_index)+1.));
  call(calls,s,e,"effect",18,{value});call(calls,s,e,"effect",22,{value});
 }
 float threshold=f(double(c.durability_index)*10.+250.);
 if(threshold<s.main_temperature){if(threshold==0)throw std::invalid_argument("nonzero damage threshold required");call(calls,s,e,"damage",3,{0});call(calls,s,e,"effect",18,{f(d(s.main_temperature)/threshold)});}
 return{s,std::move(calls)};
}
}
