#pragma once
#include "mco/driving_engine_rpm.hpp"
#include <array>
#include <cstdint>
#include <functional>
#include <optional>
#include <string>
#include <vector>
namespace mco {
struct EngineUpdateState {
  DrivingEngineRPM rpm_state{};
  std::uint32_t engine_flags = 0, vehicle_flags = 0;
  int selector_index = 0;
  std::array<std::int32_t, 8> activation_delays{};
  std::int32_t current_counter = 0;
  float override_value = 0;
  bool control_gate = false;
  float motion_metric = 0;
  std::vector<float> torque_curve;
  float effective_torque = 0, curve_torque = 0, power = 0, engagement = 0;
};
struct EngineCall {
  std::string stage;
  std::optional<std::int32_t> argument;
  bool operator==(const EngineCall &) const = default;
};
using EngineStageExecutor = std::function<std::int32_t(const EngineCall &, EngineUpdateState &)>;
struct EngineUpdateOutput { EngineUpdateState state; std::vector<EngineCall> calls; };
std::int32_t signed_engine_counter(std::int64_t value);
double curve_torque_at_rpm(const std::vector<float> &table, std::int32_t rpm);
// Recovered dispatcher, RPM and curve lookup. Every other child requires supplied behavior.
EngineUpdateOutput update_engine(EngineUpdateState state, const EngineStageExecutor &execute);
// Vehicle-path engine controller at original entry 0x548260. This executes
// the recovered control prelude and retains the observed 0x548660 RET call.
EngineUpdateOutput update_engine_system(EngineUpdateState state, const EngineStageExecutor &execute);
}
