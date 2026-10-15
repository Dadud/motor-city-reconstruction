#include "mco/engine_pipeline.hpp"
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>
#include <stdexcept>
namespace {
mco::EnginePipelineState base(){mco::EnginePipelineState s;s.rpm_state={600,9000,.7f,.4f,4000,true,.7f,100,314.15928f,3000,8500,2,175.5f,20};return s;}
mco::EnginePipelineConfig config(){mco::EnginePipelineConfig c;for(int i=0;i<22;++i)c.torque.torque_curve.push_back(100+i*13.5f);c.links.material_index=c.torque.material_index;c.links.durability_index=c.torque.durability_index;c.links.loss_index=c.torque.loss_index;c.links.third_enabled=c.torque.third_enabled;return c;}
mco::TorqueStageResult supplied(const mco::PipelineCall&a,mco::EnginePipelineState&){return {a.stage=="rpm_limit"?10000.:0.,0};}
}
int main(){
 auto s=base();auto c=config();
 {auto in=s;in.vehicle_flags=7;in.engagement=.125f;in.thermal_engagement=.9f;auto out=mco::update_engine_pipeline(in,c,supplied);assert(out.state.engagement==.125f&&out.state.thermal_engagement>.5f);}
 {auto out=mco::update_engine_pipeline(s,c,supplied);std::vector<std::string>top,nested;for(const auto&a:out.calls){if(a.domain=="dispatch")top.push_back(a.stage);if(a.domain=="torque_update")nested.push_back(a.stage);}assert((top==std::vector<std::string>{"engine_setup","engine_control","gear_link","drivetrain_loads","engagement_inputs","torque_update","wheel_drive","engine_finalize"}));assert((nested==std::vector<std::string>{"environment","rpm_update","rpm_limit"}));assert(out.state.main_temperature!=100);auto next=mco::update_engine_pipeline(out.state,c,supplied);assert(next.state.main_temperature!=out.state.main_temperature);}
 {auto in=s;in.vehicle_flags=6;auto out=mco::update_engine_pipeline(in,c,[](const mco::PipelineCall&a,mco::EnginePipelineState&state){if(a.domain=="torque_update"&&a.stage=="rpm_limit")state.vehicle_flags=7;return mco::TorqueStageResult{a.stage=="rpm_limit"?10000.:0.,0};});assert(out.state.vehicle_flags==7&&out.calls.back().stage=="drivetrain_loads");}
 {auto in=s;in.vehicle_flags=6;in.alternate_enabled=true;auto out=mco::update_engine_pipeline(in,c,[](const mco::PipelineCall&a,mco::EnginePipelineState&state){if(a.domain=="torque_update"&&a.stage=="boost"){state.gate_two=.5f;return mco::TorqueStageResult{17.5,.25f};}return mco::TorqueStageResult{a.stage=="rpm_limit"?10000.:0.,0};});assert(out.state.gate_two==.5f&&out.state.boost_observation==.25f);}
 {auto cfg=c;cfg.links.material_index=99;bool caught=false;try{mco::update_engine_pipeline(s,cfg,supplied);}catch(const std::invalid_argument&){caught=true;}assert(caught);caught=false;try{mco::update_engine_pipeline(s,c,{});}catch(const std::invalid_argument&){caught=true;}assert(caught);}
}
