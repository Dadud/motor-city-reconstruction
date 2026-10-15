#include "mco/drivetrain_links.hpp"
#include <iomanip>
#include <iostream>
#include <map>
#include <stdexcept>
namespace {
std::vector<float*> numbers(mco::DrivetrainLinksState&s){return{&s.speed,&s.normalized_rpm,&s.engagement,&s.auxiliary_temperature,&s.auxiliary_capacity,&s.condition,&s.main_temperature,&s.loss,&s.drive_scale,&s.primary_drive,&s.alternate_drive,&s.third_temperature,&s.gate_one,&s.gate_two,&s.threshold_observation,&s.request,&s.rate_two,&s.rate_one,&s.shielding_one,&s.shielding_two};}
std::vector<float*> numbers(mco::DrivetrainLinksConfig&c){return{&c.alternate_threshold,&c.thermal_gain,&c.cooling_capacity,&c.main_loss_coefficient,&c.transfer_coefficient,&c.reference,&c.upgrade_enabled,&c.upgrade_cooling,&c.upgrade_capacity};}
void mutate(mco::DrivetrainLinksState&s,const std::string&name,float value){
 if(name=="request")s.request=value;else if(name=="engagement")s.engagement=value;
 else if(name=="third_temperature")s.third_temperature=value;else if(name=="condition")s.condition=value;
 else if(name=="main_temperature")s.main_temperature=value;else throw std::invalid_argument("unsupported supplied mutation");
}
}
int main(){
 std::cout<<std::setprecision(17);std::string kind;
 while(std::cin>>kind){
  mco::DrivetrainLinksState s;mco::DrivetrainLinksConfig c;int alt,bypass,third,n;
  std::cin>>s.engine_flags>>s.vehicle_flags>>s.rpm>>s.mode>>alt>>bypass;s.alternate_enabled=alt;s.bypass=bypass;
  for(auto*p:numbers(s))std::cin>>*p;
  std::cin>>c.material_index>>c.durability_index>>c.loss_index>>third;c.third_enabled=third;
  for(auto*p:numbers(c))std::cin>>*p;
  std::cin>>n;c.mode_coefficients.resize(n);for(auto&v:c.mode_coefficients)std::cin>>v;
  std::cin>>n;std::map<int,std::vector<std::pair<std::string,float>>>mutations;
  for(int i=0;i<n;++i){int code;std::string name;float value;std::cin>>code>>name>>value;mutations[code].push_back({name,value});}
  if(!std::cin)return 2;
  auto execute=[&](const mco::LinkCall&a,mco::DrivetrainLinksState&state){if(a.stage=="damage")for(const auto&[name,value]:mutations[a.code])mutate(state,name,value);};
  auto out=kind=="gear"?mco::update_gear_link(s,c,execute):mco::update_drivetrain_loads(s,c,execute);
  auto&t=out.state;std::cout<<t.engine_flags<<' '<<t.vehicle_flags<<' '<<t.rpm<<' '<<t.mode<<' '<<t.alternate_enabled<<' '<<t.bypass;
  for(auto*p:numbers(t))std::cout<<' '<<*p;
  std::cout<<' '<<out.calls.size();
  for(const auto&a:out.calls){std::cout<<' '<<a.stage<<' '<<a.code<<' '<<a.values.size();for(auto v:a.values)std::cout<<' '<<v;}
  std::cout<<'\n';
 }
 return std::cin.eof()?0:2;
}
