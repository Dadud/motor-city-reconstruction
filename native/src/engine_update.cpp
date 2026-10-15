#include "mco/engine_update.hpp"
#include <algorithm>
#include <bit>
#include <cmath>
#include <limits>
#include <stdexcept>
#include <utility>
namespace mco {
namespace {
float stored(double v) {
  if (!std::isfinite(v) || std::abs(v)>std::numeric_limits<float>::max())
    throw std::invalid_argument("finite binary32 engine value required");
  return static_cast<float>(v);
}
void normalize(EngineUpdateState &s) {
  if (s.selector_index < 0 || s.selector_index >= 8 || s.rpm_state.limiter_rpm <= 0)
    throw std::invalid_argument("supported selector and positive limiter required");
  const auto &r=s.rpm_state;
  for (auto v:{r.idle_rpm,r.configured_max_rpm,r.target_rpm,r.rpm,r.limiter_rpm,r.gear_index})
    if(v==std::numeric_limits<std::int32_t>::min())
      throw std::invalid_argument("bounded signed RPM fields required");
  for (auto v:{r.throttle,r.normalized_rpm,r.inertia_factor,r.acceleration_input,r.angular_speed,
       r.gear_speed_factor,r.longitudinal_speed,r.acceleration_output,s.override_value,s.motion_metric,
       s.effective_torque,s.curve_torque,s.power,s.engagement}) stored(v);
  for(auto v:s.torque_curve)stored(v);
  s.rpm_state.enabled = (s.engine_flags & 1) != 0;
}
std::int32_t nearest(float v) {
  double low = std::floor(double(v)), fraction = double(v) - low;
  return static_cast<std::int32_t>(low + (fraction > .5 || (fraction == .5 && std::fmod(low,2) != 0)));
}
}
std::int32_t signed_engine_counter(std::int64_t v) {
  return std::bit_cast<std::int32_t>(static_cast<std::uint32_t>(v));
}
double curve_torque_at_rpm(const std::vector<float> &table, std::int32_t rpm) {
  if (rpm < 0 || table.size() < 2) throw std::invalid_argument("nonnegative RPM and adjacent torque knots required");
  for(auto v:table)stored(v);
  auto index = static_cast<std::size_t>(std::floor(double(rpm)*double(stored(.002))));
  if (index >= table.size()-1) throw std::invalid_argument("RPM outside supplied torque curve");
  return (double(table[index+1])-table[index])*(double(stored(rpm))-double(index)*500)*double(stored(.002))+table[index];
}
EngineUpdateOutput update_engine(EngineUpdateState s, const EngineStageExecutor &execute) {
  if (!execute) throw std::invalid_argument("engine child executor required");
  normalize(s); std::vector<EngineCall> calls;
  auto call = [&](const std::string &stage, std::optional<std::int32_t> argument = {}) {
    EngineCall action{stage,argument}; calls.push_back(action);
    auto result = execute(action,s); normalize(s); return result;
  };
  auto rpm_update = [&] {
    calls.push_back({"rpm_update",s.rpm_state.idle_rpm});
    s.rpm_state = update_driving_engine_rpm(s.rpm_state,s.rpm_state.idle_rpm);
  };
  auto fixed_rpm = [&] {
    auto &r = s.rpm_state; r.rpm = nearest(stored(double(r.limiter_rpm)*.875));
    r.angular_speed = stored(double(r.rpm)*double(stored(.10471976))); r.acceleration_output = 0;
  };
  if (!(s.engine_flags&1)) {
    if (call("interface_query",8)==0) { s.engine_flags |= 1; normalize(s); }
    else if (signed_engine_counter(std::int64_t(call("activation_counter"))-256+s.activation_delays[s.selector_index])<=s.current_counter) {
      s.engine_flags |= 1; normalize(s); call("enable_signal",1);
    }
  }
  auto flags = s.vehicle_flags;
  if (!(flags&2)) {
    if ((flags&4) && (s.engine_flags&1))
      for (const auto *stage : {"engine_setup","engine_control","gear_link","drivetrain_loads","engagement_inputs","torque_update","wheel_drive","engine_finalize"}) call(stage);
    return {std::move(s),std::move(calls)};
  }
  if (!(flags&4)) {
    if (!(flags&1) || s.override_value==0 || !(s.engine_flags&1)) {
      if (!(flags&1) || call("start_counter")<=s.current_counter) {
        if (!s.control_gate && s.motion_metric<stored(11.17575)) {
          const float fractions[]{.7f,.6f,.75f,.65f,.55f,.8f,.5f,.67f};
          auto fraction = fractions[s.selector_index]; auto &r = s.rpm_state;
          r.acceleration_input = stored(double(r.limiter_rpm)*fraction-r.rpm);
          r.throttle = std::clamp(stored(double(fraction)*double(stored(1.1))),.5f,1.f); rpm_update();
        } else call("idle_regulation");
      } else {
        auto threshold = call("interface_query",1)!=0 ? 128 : 10;
        call("start_acceleration");
        if (s.current_counter<=threshold) s.rpm_state.acceleration_input=0;
        if (!(s.engine_flags&1)) {
          s.rpm_state.rpm=0; s.rpm_state.angular_speed=0; s.effective_torque=0; s.engagement=0;
        } else rpm_update();
      }
    } else fixed_rpm();
  } else {
    if (!(s.engine_flags&1)) { s.rpm_state.rpm=0; s.rpm_state.acceleration_input=0; }
    if (s.override_value==0 || !(s.engine_flags&1)) call("torque_update"); else fixed_rpm();
  }
  auto &r=s.rpm_state; s.effective_torque=100; r.normalized_rpm=stored(double(r.rpm)/r.limiter_rpm);
  calls.push_back({"curve_lookup",r.rpm}); double torque=curve_torque_at_rpm(s.torque_curve,r.rpm);
  s.curve_torque=stored(torque); s.power=std::max(0.f,stored(torque*r.rpm*double(stored(.00010471976))));
  if ((s.vehicle_flags&1) && (s.vehicle_flags&2)) { call("gear_link"); call("drivetrain_loads"); }
  return {std::move(s),std::move(calls)};
}
}
