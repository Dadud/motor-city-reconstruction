#include "mco/recovered_vehicle_runtime.hpp"

#include <iomanip>
#include <iostream>
#include <stdexcept>
static void require(bool condition) { if (!condition) throw std::runtime_error("vehicle runtime contract failed"); }
int main() {
  mco::RecoveredVehicleRuntimeState s;
  s.vehicle.flags = 4;
  s.vehicle.linear_velocity = {1, 0, 20};
  s.vehicle.local_linear = {1, 0, 20};
  s.vehicle.alternate_speed = 12;
  s.engine.rpm_state = {600,9000,.7f,.4f,4000,true,.7f,100,314.15928f,3000,8500,2,175.5f,20};
  s.engine.rpm_state.angular_speed=static_cast<float>(3000*static_cast<double>(.10471976f));
  s.engine.drag_factor=.12f;s.engine.drag_speed=20;s.engine.effect_motion=-42;
  mco::EnginePipelineConfig c;
  for(int i=0;i<22;++i)c.torque.torque_curve.push_back(100+i*13.5f);
  c.links.material_index=c.torque.material_index;
  c.links.durability_index=c.torque.durability_index;
  c.links.loss_index=c.torque.loss_index;
  c.links.third_enabled=c.torque.third_enabled;
  mco::RecoveredVehicleRuntime runtime(s,c);
  bool rejected=false;
  try { runtime.tick({}); } catch(const std::invalid_argument&) { rejected=true; }
  require(rejected && runtime.state().completed_ticks==0);
  int tick=0;
  mco::RecoveredVehicleRuntimeHooks h;
  h.linear_enabled=[&](const auto&,const auto&) { return tick%7!=0; };
  h.vehicle=[&](const auto&a,auto&v,auto&) {
    if(a.stage=="global_mode") return tick%3==0?1.:0.;
    if(a.stage=="predict_support") for(auto&w:v.wheels) w.contact=tick%5!=0;
    if(a.stage=="tires") for(auto&w:v.wheels)w.force={0,2500.,150.};
    if(a.stage=="vehicle_gate")return 1.;
    return 0.;
  };
  h.engine=[](const auto&a,auto&e,auto&) {
    if(a.stage=="engine_finalize") e.effect_motion+=.25f;
    return mco::TorqueStageResult{a.stage=="rpm_limit"?10000.:0.,0};
  };
  // Host-side rollback is intentionally stronger than original owner mutation.
  auto broken=h;
  broken.engine=[](const auto&,auto&e,auto&)->mco::TorqueStageResult {
    e.request=99;throw std::runtime_error("synthetic failure");
  };
  rejected=false;
  try {runtime.tick(broken);}catch(const std::runtime_error&){rejected=true;}
  require(rejected && runtime.state().engine.request==s.engine.request && runtime.state().completed_ticks==0);
  std::cout<<std::setprecision(17);
  for(tick=0;tick<120;++tick) {
    auto result=runtime.tick(h);const auto&state=runtime.state();
    require(result.completed_ticks==static_cast<unsigned>(tick+1));
    std::cout<<result.branch<<' '<<result.vehicle_calls.size()<<' '<<result.engine_calls.size()<<' '
      <<state.vehicle.flags<<' '<<state.vehicle.speed<<' '<<state.vehicle.linear_velocity[0]<<' '
      <<state.vehicle.linear_velocity[1]<<' '<<state.vehicle.linear_velocity[2]<<' '
      <<state.vehicle.local_linear[2]<<' '<<state.engine.rpm_state.rpm<<' '
      <<state.engine.main_temperature<<' '<<state.engine.effective_torque<<'\n';
  }
}
