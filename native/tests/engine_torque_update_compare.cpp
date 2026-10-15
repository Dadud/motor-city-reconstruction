#include "mco/engine_torque_update.hpp"
#include <iomanip>
#include <iostream>
#include <map>
#include <stdexcept>
namespace {
std::vector<float*>numbers(mco::EngineTorqueState&s){auto&r=s.rpm_state;return{&r.throttle,&r.normalized_rpm,&r.inertia_factor,&r.acceleration_input,&r.angular_speed,&r.gear_speed_factor,&r.longitudinal_speed,&r.acceleration_output,&s.curve_torque,&s.effective_torque,&s.power,&s.engagement,&s.brake_control,&s.condition_accumulator,&s.condition_gate,&s.damage_d3c,&s.damage_d40,&s.damage_d44,&s.damage_d48,&s.damage_d4c,&s.loss,&s.auxiliary_temperature,&s.boost_observation,&s.effect_motion,&s.drag_factor,&s.drag_speed,&s.drag,&s.coupling_resistance,&s.environment_field};}
std::vector<float*>numbers(mco::EngineTorqueConfig&c){return{&c.upgrade_enabled,&c.boost_threshold,&c.boost_available,&c.exhaust_tag,&c.compression,&c.overload_coefficient,&c.torque_capacity};}
void read(mco::EngineTorqueState&s){auto&r=s.rpm_state;int bypass,alt,eo,es,en;
 std::cin>>s.engine_flags>>bypass>>s.counter>>alt>>s.boost_flag>>eo>>es>>s.environment_selector;
 s.bypass=bypass;s.alternate_enabled=alt;s.environment_override=eo;s.environment_selector_enabled=es;
 std::cin>>r.idle_rpm>>r.configured_max_rpm>>r.target_rpm>>r.rpm>>r.limiter_rpm>>r.gear_index>>en;r.enabled=en;
 for(auto*p:numbers(s))std::cin>>*p;
}
void write(mco::EngineTorqueState&s){auto&r=s.rpm_state;
 std::cout<<s.engine_flags<<' '<<s.bypass<<' '<<s.counter<<' '<<s.alternate_enabled<<' '<<s.boost_flag<<' '<<s.environment_override<<' '<<s.environment_selector_enabled<<' '<<s.environment_selector;
 std::cout<<' '<<r.idle_rpm<<' '<<r.configured_max_rpm<<' '<<r.target_rpm<<' '<<r.rpm<<' '<<r.limiter_rpm<<' '<<r.gear_index<<' '<<r.enabled;
 for(auto*p:numbers(s))std::cout<<' '<<*p;
}
void mutate(mco::EngineTorqueState&s,const std::string&name,double value){
 if(name=="loss")s.loss=static_cast<float>(value);
 else if(name=="brake_control")s.brake_control=static_cast<float>(value);
 else if(name=="effective_torque")s.effective_torque=static_cast<float>(value);
 else if(name=="curve_torque")s.curve_torque=static_cast<float>(value);
 else if(name=="rpm.rpm")s.rpm_state.rpm=static_cast<std::int32_t>(value);
 else if(name=="rpm.throttle")s.rpm_state.throttle=static_cast<float>(value);
 else throw std::invalid_argument("unsupported supplied mutation");
}
struct Mutation{std::string stage,name;double value;};
}
int main(){
 std::cout<<std::setprecision(17);
 while(std::cin.peek()!=EOF){
  mco::EngineTorqueState s;mco::EngineTorqueConfig c;read(s);if(!std::cin)return std::cin.eof()?0:2;
  int third,n;std::cin>>third>>c.loss_index>>c.material_index>>c.upgrade_index>>c.gain_mode>>c.durability_index>>c.limit_a>>c.limit_b>>c.overspeed_base>>c.overspeed_extra>>c.overload_index;c.third_enabled=third;
  for(auto*p:numbers(c))std::cin>>*p;
  std::cin>>n;c.torque_curve.resize(n);for(auto&v:c.torque_curve)std::cin>>v;
  std::cin>>n;std::map<std::string,mco::TorqueStageResult>responses;
  for(int i=0;i<n;++i){std::string name;mco::TorqueStageResult r;std::cin>>name>>r.value>>r.boost_increment;responses[name]=r;}
  std::cin>>n;std::vector<Mutation>mutations;
  for(int i=0;i<n;++i){Mutation m;std::cin>>m.stage>>m.name>>m.value;mutations.push_back(m);}
  if(!std::cin)return 2;
  auto out=mco::update_engine_torque(s,c,[&](const mco::TorqueCall&a,mco::EngineTorqueState&state){
   for(const auto&m:mutations)if(m.stage==a.stage)mutate(state,m.name,m.value);
   auto it=responses.find(a.stage);return it==responses.end()?mco::TorqueStageResult{}:it->second;
  });
  write(out.state);std::cout<<' '<<out.calls.size();
  for(const auto&a:out.calls){std::cout<<' '<<a.stage<<' '<<a.code.value_or(-1)<<' '<<a.values.size();for(auto v:a.values)std::cout<<' '<<v;}
  std::cout<<'\n';std::cin>>std::ws;
 }
}
