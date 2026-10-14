#pragma once
#include <array>
#include <cstdint>
#include <functional>
#include <optional>
#include <string>
#include <vector>
namespace mco {
using UpdateVector = std::array<double, 3>;
using UpdateMatrix = std::array<double, 9>;
struct UpdateWheel {
  bool contact = false;
  UpdateVector force{};
  std::optional<std::uint8_t> surface_record;
  int surface_class = 0;
  double primary_coefficient = 1, secondary_coefficient = .8, base_grip = 1, quality = 1;
  int wear_mode = 0, tire_type = 0;
  double spin_scale = .3, spin = 0, projected_speed = 0, local_lateral = 0, phase = 0,
         primary_angle = 0, clear_reference = 0, clear_threshold = 0;
};
struct VehicleUpdateState {
  bool active = true, tilted = false;
  double attitude = 1;
  std::uint32_t flags = 0;
  UpdateVector linear_velocity{}, angular_velocity{}, linear_acceleration{}, angular_acceleration{},
      extra_acceleration{}, local_linear{}, local_angular{}, local_acceleration{},
      local_angular_acceleration{};
  UpdateMatrix to_local{1, 0, 0, 0, 1, 0, 0, 0, 1}, to_world{1, 0, 0, 0, 1, 0, 0, 0, 1};
  std::array<UpdateWheel, 4> wheels{};
  double speed = 0, alternate_speed = 0, secondary_angle = 0, turning_radius_y = 0,
         turning_radius_x = 0, inverse_mass = .001, mass = 1000, gravity_force = 9800,
         lateral_contribution = 0, longitudinal_contribution = 0;
  double front_lever = 1, rear_lever = 1, front_moment = 0, rear_moment = 0, body_moment = 0,
         angular_scale = 1, maximum_steering = .1, front_grip_gate = 0, rear_grip_gate = 0;
  int environment_mode = 0, fallback_surface = 0, support_count = 0;
  bool orientation_disabled = false, grip_boost = false;
  std::array<double, 32> surface_coefficients = [] {
    std::array<double, 32> a{};
    a.fill(1);
    return a;
  }();
};
struct UpdateCall {
  std::string stage;
  std::optional<int> slot;
  bool operator==(const UpdateCall &) const = default;
};
using VehicleStageExecutor = std::function<double(const UpdateCall &, VehicleUpdateState &)>;
struct VehicleUpdateOutput {
  VehicleUpdateState state;
  std::vector<UpdateCall> calls;
  std::string branch;
};
UpdateVector transform_update_vector(const UpdateVector &, const UpdateMatrix &);
void apply_linear_update(VehicleUpdateState &, bool enabled);
// Every child operation and query must be supplied explicitly; missing behavior must throw.
VehicleUpdateOutput update_vehicle(VehicleUpdateState state, const VehicleStageExecutor &execute);
} // namespace mco
