#include "mco/engine_pipeline.hpp"
#include <cmath>
#include <stdexcept>
#include <utility>
namespace mco {namespace {
void normalize(EnginePipelineState&s){
 if(s.selector_index<0||s.selector_index>=8||s.thermal_mode<0||s.thermal_mode>255||s.rpm_state.idle_rpm<=0||s.rpm_state.limiter_rpm<=0)throw std::invalid_argument("supported engine pipeline fields required");
 auto&r=s.rpm_state;r.enabled=(s.engine_flags&1)!=0;
 for(auto v:{r.throttle,r.normalized_rpm,r.inertia_factor,r.acceleration_input,r.angular_speed,r.gear_speed_factor,r.longitudinal_speed,r.acceleration_output,
 s.curve_torque,s.effective_torque,s.power,s.engagement,s.brake_control,s.condition_accumulator,s.condition_gate,s.damage_d3c,s.damage_d40,s.damage_d44,s.damage_d48,s.damage_d4c,s.loss,s.auxiliary_temperature,s.boost_observation,s.effect_motion,s.drag_factor,s.drag_speed,s.drag,s.coupling_resistance,s.environment_field,
 s.override_value,s.motion_metric,s.thermal_engagement,s.auxiliary_capacity,s.condition,s.main_temperature,s.drive_scale,s.primary_drive,s.alternate_drive,s.third_temperature,s.gate_one,s.gate_two,s.request,s.rate_two,s.rate_one,s.shielding_one,s.shielding_two})if(!std::isfinite(v))throw std::invalid_argument("finite engine pipeline state required");
}
void validate(const EnginePipelineConfig&c){
 if(c.torque.material_index!=c.links.material_index||c.torque.durability_index!=c.links.durability_index||c.torque.loss_index!=c.links.loss_index||c.torque.third_enabled!=c.links.third_enabled||c.torque.upgrade_enabled!=c.links.upgrade_enabled||c.torque.boost_threshold!=c.links.alternate_threshold)throw std::invalid_argument("inconsistent shared engine catalogue fields");
}
EngineUpdateState dispatch(const EnginePipelineState&s,const EnginePipelineConfig&c){
 EngineUpdateState d;d.rpm_state=s.rpm_state;d.engine_flags=s.engine_flags;d.vehicle_flags=s.vehicle_flags;
 d.selector_index=s.selector_index;d.activation_delays=s.activation_delays;d.current_counter=s.counter;
 d.override_value=s.override_value;d.control_gate=s.control_gate;d.motion_metric=s.motion_metric;
 d.torque_curve=c.torque.torque_curve;d.effective_torque=s.effective_torque;d.curve_torque=s.curve_torque;d.power=s.power;d.engagement=s.engagement;return d;
}
void import_dispatch(const EngineUpdateState&d,EnginePipelineState&s){
 s.rpm_state=d.rpm_state;s.engine_flags=d.engine_flags;s.vehicle_flags=d.vehicle_flags;s.selector_index=d.selector_index;
 s.activation_delays=d.activation_delays;s.counter=d.current_counter;s.override_value=d.override_value;
 s.control_gate=d.control_gate;s.motion_metric=d.motion_metric;s.effective_torque=d.effective_torque;s.curve_torque=d.curve_torque;s.power=d.power;s.engagement=d.engagement;
}
DrivetrainLinksState links(const EnginePipelineState&s){
 DrivetrainLinksState t;t.engine_flags=s.engine_flags;t.vehicle_flags=s.vehicle_flags;t.rpm=s.rpm_state.rpm;
 t.mode=s.thermal_mode;t.alternate_enabled=s.alternate_enabled;t.bypass=s.bypass;t.speed=s.rpm_state.longitudinal_speed;
 t.normalized_rpm=s.rpm_state.normalized_rpm;t.engagement=s.thermal_engagement;t.auxiliary_temperature=s.auxiliary_temperature;
 t.auxiliary_capacity=s.auxiliary_capacity;t.condition=s.condition;t.main_temperature=s.main_temperature;t.loss=s.loss;
 t.drive_scale=s.drive_scale;t.primary_drive=s.primary_drive;t.alternate_drive=s.alternate_drive;t.third_temperature=s.third_temperature;
 t.gate_one=s.gate_one;t.gate_two=s.gate_two;t.threshold_observation=s.boost_observation;t.request=s.request;
 t.rate_two=s.rate_two;t.rate_one=s.rate_one;t.shielding_one=s.shielding_one;t.shielding_two=s.shielding_two;return t;
}
void import_links(const DrivetrainLinksState&t,EnginePipelineState&s){
 s.engine_flags=t.engine_flags;s.vehicle_flags=t.vehicle_flags;s.rpm_state.rpm=t.rpm;s.thermal_mode=t.mode;
 s.alternate_enabled=t.alternate_enabled;s.bypass=t.bypass;s.rpm_state.longitudinal_speed=t.speed;
 s.rpm_state.normalized_rpm=t.normalized_rpm;s.thermal_engagement=t.engagement;s.auxiliary_temperature=t.auxiliary_temperature;
 s.auxiliary_capacity=t.auxiliary_capacity;s.condition=t.condition;s.main_temperature=t.main_temperature;s.loss=t.loss;
 s.drive_scale=t.drive_scale;s.primary_drive=t.primary_drive;s.alternate_drive=t.alternate_drive;s.third_temperature=t.third_temperature;
 s.gate_one=t.gate_one;s.gate_two=t.gate_two;s.boost_observation=t.threshold_observation;s.request=t.request;
 s.rate_two=t.rate_two;s.rate_one=t.rate_one;s.shielding_one=t.shielding_one;s.shielding_two=t.shielding_two;
}
}
EnginePipelineOutput update_engine_pipeline(EnginePipelineState s,const EnginePipelineConfig&c,const PipelineStageExecutor&execute){
 if(!execute)throw std::invalid_argument("explicit engine pipeline executor required");validate(c);normalize(s);
 std::vector<std::vector<PipelineCall>>nested;
 auto external=[&](const PipelineCall&a){auto result=execute(a,s);normalize(s);return result;};
 auto out=update_engine(dispatch(s,c),[&](const EngineCall&a,EngineUpdateState&d)->std::int32_t{
  import_dispatch(d,s);nested.emplace_back();auto&child_calls=nested.back();
  if(a.stage=="torque_update"){
   auto t=update_engine_torque(static_cast<EngineTorqueState>(s),c.torque,[&](const TorqueCall&child,EngineTorqueState&state){
    static_cast<EngineTorqueState&>(s)=state;
    auto result=external({"torque_update",child.stage,child.code,child.values});state=static_cast<EngineTorqueState>(s);return result;
   });
   static_cast<EngineTorqueState&>(s)=t.state;
   for(const auto&child:t.calls)child_calls.push_back({"torque_update",child.stage,child.code,child.values});
  }else if(a.stage=="gear_link"||a.stage=="drivetrain_loads"){
   auto method=a.stage=="gear_link"?update_gear_link:update_drivetrain_loads;
   auto t=method(links(s),c.links,[&](const LinkCall&child,DrivetrainLinksState&state){
    import_links(state,s);std::vector<double>values(child.values.begin(),child.values.end());
    external({a.stage,child.stage,child.code,std::move(values)});state=links(s);
   });
   import_links(t.state,s);
   for(const auto&child:t.calls){std::vector<double>values(child.values.begin(),child.values.end());child_calls.push_back({a.stage,child.stage,child.code,std::move(values)});}
  }else{
   auto result=external({"dispatch",a.stage,a.argument,{}});d=dispatch(s,c);
   if(!std::isfinite(result.value)||std::floor(result.value)!=result.value||result.value < -2147483648.||result.value>2147483647.)throw std::invalid_argument("signed dispatcher child result required");
   return static_cast<std::int32_t>(result.value);
  }
  normalize(s);d=dispatch(s,c);return 0;
 });
 import_dispatch(out.state,s);normalize(s);std::vector<PipelineCall>calls;std::size_t index=0;
 for(const auto&a:out.calls){
  calls.push_back({"dispatch",a.stage,a.argument,{}});
  if(a.stage!="rpm_update"&&a.stage!="curve_lookup"){for(const auto&child:nested.at(index++))calls.push_back(child);}
 }
 return{s,std::move(calls)};
}
}
