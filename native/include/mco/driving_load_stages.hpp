#pragma once

#include "mco/vehicle_update.hpp"
#include <array>
#include <cstdint>

namespace mco {
// Explicit component observations not present in VehicleUpdateState.
struct DrivingLoadParameters {
  double pitch, bank, configuration_mass, wheelbase, front_track, rear_track;
  double height_parameter, front_offset, rear_offset;
  std::array<double, 4> wheel_scales; // LF/RF/LR/RR calculation order.
  double suspension_pitch, mass_offset, front_weight_parameter, rear_weight_parameter;
  double gear_factor, torque, body_secondary_angle;
  std::int32_t component_mode;
};

// Handles the three recovered load stages and delegates all other stages.
VehicleStageExecutor make_driving_load_executor(DrivingLoadParameters parameters,
                                                 VehicleStageExecutor remaining_stages);
} // namespace mco
