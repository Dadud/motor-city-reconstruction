#include "mco/engine_torque_update.hpp"
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>
#include <stdexcept>
namespace {
mco::EngineTorqueState base(){mco::EngineTorqueState s;s.rpm_state={600,9000,.7f,.4f,4000,true,.7f,100,314.15928f,3000,8500,2,175.5f,20};return s;}
mco::EngineTorqueConfig config(){mco::EngineTorqueConfig c;for(int i=0;i<22;++i)c.torque_curve.push_back(100+i*13.5f);return c;}
}
int main(){
 auto s=base();auto c=config();auto supplied=[](const mco::TorqueCall&a,mco::EngineTorqueState&){return mco::TorqueStageResult{a.stage=="rpm_limit"?10000.:0.,0};};
 {auto in=s;in.engine_flags=0;auto out=mco::update_engine_torque(in,c,supplied);assert(out.state.rpm_state.rpm==0&&out.state.engagement==0&&out.state.curve_torque==100&&out.state.effective_torque==0);}
 {auto in=s;in.rpm_state.rpm=599;auto out=mco::update_engine_torque(in,c,supplied);assert(out.state.rpm_state.rpm>=600&&out.state.engagement==.25f&&out.state.curve_torque==100);}
 {auto in=s;in.alternate_enabled=true;auto out=mco::update_engine_torque(in,c,[](const mco::TorqueCall&a,mco::EngineTorqueState&){return a.stage=="boost"?mco::TorqueStageResult{17.5,.25f}:mco::TorqueStageResult{10000,0};});assert(out.state.boost_flag==1&&out.state.boost_observation==.25f&&out.calls[0].stage=="boost");}
 {auto in=s;in.rpm_state.throttle=0;in.brake_control=.5f;in.engine_flags=9;auto a=mco::update_engine_torque(in,c,supplied);auto b=mco::update_engine_torque(in,c,[](const mco::TorqueCall&a,mco::EngineTorqueState&){return mco::TorqueStageResult{a.stage=="brake_query"?1.:10000.,0};});assert(a.state.effective_torque*.5f==b.state.effective_torque&&b.state.engine_flags==1);}
 {auto in=s;in.damage_d40=.5f;in.damage_d4c=1;auto out=mco::update_engine_torque(in,c,[](const mco::TorqueCall&a,mco::EngineTorqueState&){return mco::TorqueStageResult{a.stage=="pulse"?1.5:10000,0};});assert(out.calls[0].stage=="pulse"&&out.calls[0].values[1]==.5);}
 {auto in=s;auto cfg=c;cfg.durability_index=1;cfg.overspeed_base=1000;cfg.overload_index=1;cfg.torque_capacity=50;in.rpm_state.rpm=8000;in.rpm_state.angular_speed=static_cast<float>(8000.*double(.10471976f));in.rpm_state.throttle=.9f;
  auto out=mco::update_engine_torque(in,cfg,[](const mco::TorqueCall&,mco::EngineTorqueState&){return mco::TorqueStageResult{2500,0};});std::vector<int>codes;for(const auto&a:out.calls)if(a.stage=="damage")codes.push_back(*a.code);assert((codes==std::vector<int>{7,9,14,8,12}));}
 {bool caught=false;try{mco::update_engine_torque(s,c,{});}catch(const std::invalid_argument&){caught=true;}assert(caught);}
}
