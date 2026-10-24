#include "mco/driving_load_stages.hpp"
#include "mco/load_transfer.hpp"
#include "mco/normal_load.hpp"
#include "mco/suspension_load_correction.hpp"
#include <cstddef>
#include <stdexcept>
#include <utility>

namespace mco {
namespace {
constexpr std::array<std::size_t, 4> load_order{0, 1, 3, 2};

std::array<double, 4> read_loads(const VehicleUpdateState &state) {
  std::array<double, 4> loads{};
  for (std::size_t i = 0; i < load_order.size(); ++i)
    loads[i] = state.wheels[load_order[i]].force[1];
  return loads;
}

void write_y_loads(VehicleUpdateState &state, const std::array<float, 4> &loads) {
  for (std::size_t i = 0; i < load_order.size(); ++i)
    state.wheels[load_order[i]].force[1] = loads[i];
}
} // namespace

VehicleStageExecutor make_driving_load_executor(DrivingLoadParameters p,
                                                 VehicleStageExecutor remaining_stages) {
  return [p, remaining_stages = std::move(remaining_stages)](
             const UpdateCall &call, VehicleUpdateState &state) -> double {
    if (call.stage == "normal_loads") {
      NormalLoadInput input{};
      for (std::size_t i = 0; i < load_order.size(); ++i)
        input.support[i] = state.wheels[load_order[i]].contact;
      input.pitch = p.pitch;
      input.bank = p.bank;
      input.mass = p.configuration_mass;
      input.wheelbase = p.wheelbase;
      input.front_track = p.front_track;
      input.rear_track = p.rear_track;
      input.height_parameter = p.height_parameter;
      input.front_lever = state.front_lever;
      input.rear_lever = state.rear_lever;
      input.speed = state.speed;
      input.curvature_scale = state.turning_radius_y;
      input.vertical_correction = state.local_acceleration[1];
      input.wheel_scales = p.wheel_scales;
      const auto forces = normal_force_vectors(input);
      for (std::size_t i = 0; i < load_order.size(); ++i)
        state.wheels[load_order[i]].force = {
            forces[i][0], forces[i][1], forces[i][2]};
      return 0;
    }
    if (call.stage == "load_transfer") {
      LoadTransferInput input{};
      input.loads = read_loads(state);
      input.attitude = p.pitch;
      input.longitudinal_acceleration = state.local_acceleration[2];
      input.lateral_acceleration = state.local_acceleration[0];
      input.speed = state.speed;
      input.mass = p.configuration_mass;
      input.wheelbase = p.wheelbase;
      input.front_track = p.front_track;
      input.rear_track = p.rear_track;
      input.height_parameter = p.height_parameter;
      input.front_offset = p.front_offset;
      input.rear_offset = p.rear_offset;
      write_y_loads(state, transfer_load(input));
      return 0;
    }
    if (call.stage == "suspension_loads") {
      SuspensionLoadInput input{};
      input.loads = read_loads(state);
      for (std::size_t i = 0; i < load_order.size(); ++i)
        input.support[i] = state.wheels[load_order[i]].contact;
      input.attitude = p.pitch;
      input.enabled = state.support_count != 0;
      input.speed = state.speed;
      input.bank_angle = p.body_secondary_angle;
      input.pitch_angle = p.suspension_pitch;
      input.mass = p.configuration_mass;
      input.mass_offset = p.mass_offset;
      input.front_weight_parameter = p.front_weight_parameter;
      input.rear_weight_parameter = p.rear_weight_parameter;
      input.front_lever = state.front_lever;
      input.rear_lever = state.rear_lever;
      input.wheelbase = p.wheelbase;
      input.rear_track = p.rear_track;
      input.gear_factor = p.gear_factor;
      input.torque = p.torque;
      input.component_mode = p.component_mode;
      input.disable_torque = (state.flags & 2) != 0;
      write_y_loads(state, correct_suspension_load(input));
      return 0;
    }
    if (!remaining_stages)
      throw std::invalid_argument("executor for unrecovered vehicle stages required");
    return remaining_stages(call, state);
  };
}
} // namespace mco
