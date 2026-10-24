#include "mco/engine_update.hpp"
#include <iomanip>
#include <iostream>
#include <map>
#include <stdexcept>
namespace {
void read(mco::EngineUpdateState &s) {
 auto &r=s.rpm_state; int enabled,gate;
 std::cin >> s.engine_flags >> s.vehicle_flags >> s.selector_index >> s.current_counter >> gate;
 s.control_gate=gate;
 for(auto &x:s.activation_delays) std::cin>>x;
 std::cin >> r.idle_rpm >> r.configured_max_rpm >> r.target_rpm >> r.rpm >> r.limiter_rpm >> r.gear_index >> enabled;
 r.enabled=enabled;
 std::cin >> r.throttle >> r.normalized_rpm >> r.inertia_factor >> r.acceleration_input >> r.angular_speed >> r.gear_speed_factor >> r.longitudinal_speed >> r.acceleration_output;
 std::cin >> s.override_value >> s.motion_metric >> s.effective_torque >> s.curve_torque >> s.power >> s.engagement;
 int n;std::cin>>n;s.torque_curve.resize(n);for(auto &x:s.torque_curve)std::cin>>x;
}
void write(const mco::EngineUpdateState &s) {
 const auto &r=s.rpm_state;
 std::cout<<s.engine_flags<<' '<<s.vehicle_flags<<' '<<s.selector_index<<' '<<s.current_counter<<' '<<s.control_gate;
 for(auto x:s.activation_delays)std::cout<<' '<<x;
 std::cout<<' '<<r.idle_rpm<<' '<<r.configured_max_rpm<<' '<<r.target_rpm<<' '<<r.rpm<<' '<<r.limiter_rpm<<' '<<r.gear_index<<' '<<r.enabled;
 for(auto x:{r.throttle,r.normalized_rpm,r.inertia_factor,r.acceleration_input,r.angular_speed,r.gear_speed_factor,r.longitudinal_speed,r.acceleration_output,s.override_value,s.motion_metric,s.effective_torque,s.curve_torque,s.power,s.engagement})std::cout<<' '<<x;
 std::cout<<' '<<s.torque_curve.size();for(auto x:s.torque_curve)std::cout<<' '<<x;
}
void mutate(mco::EngineUpdateState &s,const std::string &n,double v) {
 if(n=="engine_flags")s.engine_flags=static_cast<std::uint32_t>(v);
 else if(n=="vehicle_flags")s.vehicle_flags=static_cast<std::uint32_t>(v);
 else if(n=="control_gate")s.control_gate=v!=0;
 else if(n=="motion_metric")s.motion_metric=static_cast<float>(v);
 else if(n=="effective_torque")s.effective_torque=static_cast<float>(v);
 else if(n=="engagement")s.engagement=static_cast<float>(v);
 else if(n=="override_value")s.override_value=static_cast<float>(v);
 else if(n=="rpm.rpm")s.rpm_state.rpm=static_cast<std::int32_t>(v);
 else if(n=="rpm.limiter_rpm")s.rpm_state.limiter_rpm=static_cast<std::int32_t>(v);
 else if(n=="rpm.acceleration_input")s.rpm_state.acceleration_input=static_cast<float>(v);
 else if(n=="rpm.angular_speed")s.rpm_state.angular_speed=static_cast<float>(v);
 else if(n=="rpm.throttle")s.rpm_state.throttle=static_cast<float>(v);
 else throw std::invalid_argument("unsupported supplied mutation: "+n);
}
struct Mutation {std::string stage,name;double value;};
}
int main(int argc,char **argv){
 bool vehicle_system=argc>1 && std::string(argv[1])=="--vehicle-system";
 std::cout<<std::setprecision(17);
 while(std::cin.peek()!=EOF){
  mco::EngineUpdateState s;read(s);if(!std::cin)return std::cin.eof()?0:2;
  int n;std::cin>>n;std::map<std::string,std::int32_t> observations;
  for(int i=0;i<n;++i){std::string name;std::int32_t value;std::cin>>name>>value;observations[name]=value;}
  std::cin>>n;std::vector<Mutation> mutations;
  for(int i=0;i<n;++i){Mutation m;std::cin>>m.stage>>m.name>>m.value;mutations.push_back(m);}
  if(!std::cin)return 2;
  auto execute=[&](const mco::EngineCall &c,mco::EngineUpdateState &state){
   for(const auto &m:mutations)if(m.stage==c.stage)mutate(state,m.name,m.value);
   std::string key=c.stage=="interface_query"?"query_"+std::to_string(*c.argument):c.stage;
   auto it=observations.find(key);return it==observations.end()?0:it->second;
  };
  auto out=vehicle_system?mco::update_engine_system(s,execute):mco::update_engine(s,execute);
  write(out.state);std::cout<<' '<<out.calls.size();for(const auto &c:out.calls)std::cout<<' '<<c.stage<<' '<<c.argument.value_or(-1);std::cout<<'\n';
  std::cin>>std::ws;
 }
}
