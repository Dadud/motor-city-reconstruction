#include "mco/engine_pipeline.hpp"
#include <iomanip>
#include <iostream>
#include <map>
#include <stdexcept>
namespace {
std::vector<float*>numbers(mco::EnginePipelineState&s){auto&r=s.rpm_state;return{&r.throttle,&r.normalized_rpm,&r.inertia_factor,&r.acceleration_input,&r.angular_speed,&r.gear_speed_factor,&r.longitudinal_speed,&r.acceleration_output,&s.curve_torque,&s.effective_torque,&s.power,&s.engagement,&s.brake_control,&s.condition_accumulator,&s.condition_gate,&s.damage_d3c,&s.damage_d40,&s.damage_d44,&s.damage_d48,&s.damage_d4c,&s.loss,&s.auxiliary_temperature,&s.boost_observation,&s.effect_motion,&s.drag_factor,&s.drag_speed,&s.drag,&s.coupling_resistance,&s.environment_field,&s.override_value,&s.motion_metric,&s.thermal_engagement,&s.auxiliary_capacity,&s.condition,&s.main_temperature,&s.drive_scale,&s.primary_drive,&s.alternate_drive,&s.third_temperature,&s.gate_one,&s.gate_two,&s.request,&s.rate_two,&s.rate_one,&s.shielding_one,&s.shielding_two};}
std::vector<float*>numbers(mco::EnginePipelineConfig&c){return{&c.torque.upgrade_enabled,&c.torque.boost_threshold,&c.torque.boost_available,&c.torque.exhaust_tag,&c.torque.compression,&c.torque.overload_coefficient,&c.torque.torque_capacity,&c.links.thermal_gain,&c.links.cooling_capacity,&c.links.main_loss_coefficient,&c.links.transfer_coefficient,&c.links.reference,&c.links.upgrade_cooling,&c.links.upgrade_capacity};}
void read(mco::EnginePipelineState&s){auto&r=s.rpm_state;int bypass,alt,eo,es,en,gate;
 std::cin>>s.engine_flags>>bypass>>s.counter>>alt>>s.boost_flag>>eo>>es>>s.environment_selector;
 s.bypass=bypass;s.alternate_enabled=alt;s.environment_override=eo;s.environment_selector_enabled=es;
 std::cin>>r.idle_rpm>>r.configured_max_rpm>>r.target_rpm>>r.rpm>>r.limiter_rpm>>r.gear_index>>en;r.enabled=en;
 std::cin>>s.vehicle_flags>>s.selector_index>>gate>>s.thermal_mode;s.control_gate=gate;
 for(auto&v:s.activation_delays)std::cin>>v;
 for(auto*p:numbers(s))std::cin>>*p;
}
void write(mco::EnginePipelineState&s){auto&r=s.rpm_state;
 std::cout<<s.engine_flags<<' '<<s.bypass<<' '<<s.counter<<' '<<s.alternate_enabled<<' '<<s.boost_flag<<' '<<s.environment_override<<' '<<s.environment_selector_enabled<<' '<<s.environment_selector;
 std::cout<<' '<<r.idle_rpm<<' '<<r.configured_max_rpm<<' '<<r.target_rpm<<' '<<r.rpm<<' '<<r.limiter_rpm<<' '<<r.gear_index<<' '<<r.enabled;
 std::cout<<' '<<s.vehicle_flags<<' '<<s.selector_index<<' '<<s.control_gate<<' '<<s.thermal_mode;
 for(auto v:s.activation_delays)std::cout<<' '<<v;for(auto*p:numbers(s))std::cout<<' '<<*p;
}
void mutate(mco::EnginePipelineState&s,const std::string&name,double value){
 if(name=="thermal_engagement")s.thermal_engagement=static_cast<float>(value);
 else if(name=="engagement")s.engagement=static_cast<float>(value);
 else if(name=="vehicle_flags")s.vehicle_flags=static_cast<std::uint32_t>(value);
 else if(name=="boost_observation")s.boost_observation=static_cast<float>(value);
 else if(name=="main_temperature")s.main_temperature=static_cast<float>(value);
 else if(name=="gate_two")s.gate_two=static_cast<float>(value);
 else if(name=="rpm.throttle")s.rpm_state.throttle=static_cast<float>(value);
 else throw std::invalid_argument("unsupported supplied mutation");
}
struct Mutation{std::string domain,stage,name;double value;};
}
int main(){
 std::cout<<std::setprecision(17);int ticks;
 while(std::cin>>ticks){
  mco::EnginePipelineState s;mco::EnginePipelineConfig c;read(s);int third,n;
  std::cin>>third>>c.torque.loss_index>>c.torque.material_index>>c.torque.upgrade_index>>c.torque.gain_mode>>c.torque.durability_index>>c.torque.limit_a>>c.torque.limit_b>>c.torque.overspeed_base>>c.torque.overspeed_extra>>c.torque.overload_index;c.torque.third_enabled=third;
  for(auto*p:numbers(c))std::cin>>*p;
  c.links.material_index=c.torque.material_index;c.links.durability_index=c.torque.durability_index;c.links.loss_index=c.torque.loss_index;c.links.third_enabled=c.torque.third_enabled;c.links.upgrade_enabled=c.torque.upgrade_enabled;c.links.alternate_threshold=c.torque.boost_threshold;
  std::cin>>n;c.torque.torque_curve.resize(n);for(auto&v:c.torque.torque_curve)std::cin>>v;
  std::cin>>n;c.links.mode_coefficients.resize(n);for(auto&v:c.links.mode_coefficients)std::cin>>v;
  std::cin>>n;std::map<std::string,mco::TorqueStageResult>responses;
  for(int i=0;i<n;++i){std::string name;mco::TorqueStageResult r;std::cin>>name>>r.value>>r.boost_increment;responses[name]=r;}
  std::cin>>n;std::vector<Mutation>mutations;for(int i=0;i<n;++i){Mutation m;std::cin>>m.domain>>m.stage>>m.name>>m.value;mutations.push_back(m);}
  if(!std::cin)return 2;
  for(int tick=0;tick<ticks;++tick){
   if(tick)++s.counter;
   auto out=mco::update_engine_pipeline(s,c,[&](const mco::PipelineCall&a,mco::EnginePipelineState&state){
    for(const auto&m:mutations)if(m.domain==a.domain&&m.stage==a.stage)mutate(state,m.name,m.value);
    std::string key=a.stage=="interface_query"?"query_"+std::to_string(*a.code):a.stage;
    auto it=responses.find(key);return it==responses.end()?mco::TorqueStageResult{}:it->second;
   });
   s=out.state;write(s);std::cout<<' '<<out.calls.size();
   for(const auto&a:out.calls){std::cout<<' '<<a.domain<<' '<<a.stage<<' '<<a.code.value_or(-1)<<' '<<a.values.size();for(auto v:a.values)std::cout<<' '<<v;}
   std::cout<<'\n';
  }
 }
 return std::cin.eof()?0:2;
}
