#include "mco/recovered_vehicle_runtime.hpp"
#include <limits>
#include <stdexcept>
#include <utility>
namespace mco {
namespace {
void read_vehicle(const VehicleUpdateState& v, EnginePipelineState& e) {
  // Same +owner aliases already established by client/driving_engine.py.
  e.vehicle_flags = v.flags;
  e.effect_motion = static_cast<float>(v.speed);
  e.rpm_state.longitudinal_speed = static_cast<float>(v.local_linear[2]);
}
void publish_engine(const EnginePipelineState& e, VehicleUpdateState& v) {
  v.flags = e.vehicle_flags;
  v.speed = e.effect_motion;
  v.local_linear[2] = e.rpm_state.longitudinal_speed;
}
}
RecoveredVehicleRuntime::RecoveredVehicleRuntime(RecoveredVehicleRuntimeState s, EnginePipelineConfig c)
    : state_(std::move(s)), config_(std::move(c)) {}
RecoveredVehicleRuntimeTick RecoveredVehicleRuntime::tick(const RecoveredVehicleRuntimeHooks& h) {
  if (!h.vehicle || !h.engine || !h.linear_enabled)
    throw std::invalid_argument("vehicle, engine and linear enable producers are mandatory");
  if (state_.completed_ticks == std::numeric_limits<std::uint64_t>::max())
    throw std::overflow_error("runtime tick counter exhausted");
  auto next = state_;
  std::vector<PipelineCall> engine_calls;
  auto out = update_vehicle(next.vehicle, [&](const UpdateCall& a, VehicleUpdateState& v) {
    if (a.stage == "linear_update") {
      apply_linear_update(v, h.linear_enabled(v, next.engine));
      return 0.;
    }
    if (a.stage != "engine") return h.vehicle(a, v, next.engine);
    read_vehicle(v, next.engine);
    auto e = update_engine_pipeline(next.engine, config_, [&](const PipelineCall& call, EnginePipelineState& owner) {
      publish_engine(owner, v);
      auto result = h.engine(call, owner, v);
      publish_engine(owner, v);
      return result;
    });
    next.engine = std::move(e.state);
    publish_engine(next.engine, v);
    engine_calls.insert(engine_calls.end(), e.calls.begin(), e.calls.end());
    return 0.;
  });
  next.vehicle = std::move(out.state);
  ++next.completed_ticks;
  state_ = std::move(next);
  return {std::move(out.branch), std::move(out.calls), std::move(engine_calls), state_.completed_ticks};
}
}
