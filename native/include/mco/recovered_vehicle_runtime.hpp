#pragma once
#include "mco/engine_pipeline.hpp"
#include "mco/vehicle_update.hpp"
#include <cstdint>

namespace mco {
// Integration adapter, not another recovered function. The original dispatcher
// and engine bodies retain their own evidence and arithmetic boundaries.
struct RecoveredVehicleRuntimeState {
  VehicleUpdateState vehicle;
  EnginePipelineState engine;
  std::uint64_t completed_ticks = 0;
};
struct RecoveredVehicleRuntimeHooks {
  // All unresolved vehicle children/queries are mandatory supplied behavior.
  std::function<double(const UpdateCall&, VehicleUpdateState&, EnginePipelineState&)> vehicle;
  // During an engine callback, shared flags/speed/longitudinal speed are owned
  // by engine; mutate those aliases through engine, not vehicle.
  std::function<TorqueStageResult(const PipelineCall&, EnginePipelineState&, VehicleUpdateState&)> engine;
  // Recovered linear integration still requires the original enable producer.
  std::function<bool(const VehicleUpdateState&, const EnginePipelineState&)> linear_enabled;
};
struct RecoveredVehicleRuntimeTick {
  std::string branch;
  std::vector<UpdateCall> vehicle_calls;
  std::vector<PipelineCall> engine_calls;
  std::uint64_t completed_ticks;
};
class RecoveredVehicleRuntime {
 public:
  RecoveredVehicleRuntime(RecoveredVehicleRuntimeState, EnginePipelineConfig);
  const RecoveredVehicleRuntimeState& state() const noexcept { return state_; }
  // A thrown callback leaves owned state unchanged. External I/O effects are
  // not transactional; record those outside this deterministic adapter.
  RecoveredVehicleRuntimeTick tick(const RecoveredVehicleRuntimeHooks&);
 private:
  RecoveredVehicleRuntimeState state_;
  EnginePipelineConfig config_;
};
}
