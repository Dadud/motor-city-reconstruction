#include "mco/vehicle_update.hpp"
#include <algorithm>
#include <cmath>
#include <limits>
#include <stdexcept>
namespace mco {
namespace {
// Arithmetic stays double until an observed original float32 memory store.
double stored(double v) {
  if (!std::isfinite(v) || std::abs(v) > std::numeric_limits<float>::max())
    throw std::invalid_argument("finite float32 controller value required");
  return static_cast<float>(v);
}
template <std::size_t N> void normalize(std::array<double, N> &a) {
  for (auto &v : a)
    v = stored(v);
}
UpdateVector increment(const UpdateVector &v, const UpdateVector &a) {
  return {stored(v[0] + a[0] * .03125), stored(v[1] + a[1] * .03125), stored(v[2] + a[2] * .03125)};
}
void normalize(VehicleUpdateState &s) {
  for (auto *v : {&s.attitude,
                  &s.speed,
                  &s.alternate_speed,
                  &s.secondary_angle,
                  &s.turning_radius_y,
                  &s.turning_radius_x,
                  &s.inverse_mass,
                  &s.mass,
                  &s.gravity_force,
                  &s.lateral_contribution,
                  &s.longitudinal_contribution,
                  &s.front_lever,
                  &s.rear_lever,
                  &s.front_moment,
                  &s.rear_moment,
                  &s.body_moment,
                  &s.angular_scale,
                  &s.maximum_steering,
                  &s.front_grip_gate,
                  &s.rear_grip_gate})
    *v = stored(*v);
  for (auto *a : {&s.linear_velocity, &s.angular_velocity, &s.linear_acceleration,
                  &s.angular_acceleration, &s.extra_acceleration, &s.local_linear, &s.local_angular,
                  &s.local_acceleration, &s.local_angular_acceleration})
    normalize(*a);
  normalize(s.to_local);
  normalize(s.to_world);
  normalize(s.surface_coefficients);
  for (auto &w : s.wheels) {
    normalize(w.force);
    for (auto *v : {&w.primary_coefficient, &w.secondary_coefficient, &w.base_grip, &w.quality,
                    &w.spin_scale, &w.spin, &w.projected_speed, &w.local_lateral, &w.phase,
                    &w.primary_angle, &w.clear_reference, &w.clear_threshold})
      *v = stored(*v);
  }
  if (s.fallback_surface < 0 || s.fallback_surface >= 32)
    throw std::invalid_argument("fallback surface outside table");
}
} // namespace
UpdateVector transform_update_vector(const UpdateVector &v, const UpdateMatrix &m) {
  // Preserve the row-vector product order; rounding happens only at the result store.
  UpdateVector out{};
  for (int i = 0; i < 3; ++i)
    out[i] = stored((v[0] * m[i] + v[1] * m[3 + i]) + v[2] * m[6 + i]);
  return out;
}
void apply_linear_update(VehicleUpdateState &s, bool enabled) {
  if (enabled) {
    s.linear_velocity = increment(s.linear_velocity, s.linear_acceleration);
    return;
  }
  const auto linear = transform_update_vector(s.linear_velocity, s.to_local),
             angular = transform_update_vector(s.angular_velocity, s.to_local);
  s.local_linear = {0, linear[1], 0};
  s.local_angular = {angular[0], 0, angular[2]};
  s.linear_velocity = transform_update_vector(s.local_linear, s.to_world);
  s.angular_velocity = transform_update_vector(s.local_angular, s.to_world);
  s.linear_acceleration = {};
  s.angular_acceleration = {};
}
VehicleUpdateOutput update_vehicle(VehicleUpdateState s, const VehicleStageExecutor &execute) {
  if (!execute)
    throw std::invalid_argument("child-stage executor required");
  normalize(s);
  std::vector<UpdateCall> calls;
  auto call = [&](const char *name, std::optional<int> slot = std::nullopt) {
    UpdateCall action{name, slot};
    calls.push_back(action);
    const double result = execute(action, s);
    // Child effects are writes to binary32 owner fields, before caller tests.
    normalize(s);
    return result;
  };
  auto project = [&] { s.local_linear = transform_update_vector(s.linear_velocity, s.to_local); };
  auto angular_world = [&] {
    s.angular_acceleration = transform_update_vector(s.local_angular_acceleration, s.to_world);
  };
  auto tail = [&] {
    call("post_vehicle");
    if (call("followup_enabled") && call("followup_ready"))
      call("followup");
  };
  auto finish = [&](const char *branch) { return VehicleUpdateOutput{s, calls, branch}; };
  const auto mode = call("global_mode");
  if (!s.active)
    return finish("inactive");
  if (mode) {
    s.speed = s.alternate_speed;
    s.local_angular = transform_update_vector(s.angular_velocity, s.to_local);
    project();
    call("predict_support");
    call("prepare_vehicle");
    call("control_update");
    const double steering = stored(s.maximum_steering * call("steering_angle"));
    call("project_wheels");
    for (int i = 0; i < 4; ++i) {
      auto &w = s.wheels[i];
      w.force = {};
      if (w.contact)
        w.force = {0, stored(s.mass * stored(2.4525)), 0};
      if (i < 2)
        w.primary_angle = steering;
      if (w.spin_scale != 0) {
        const double ratio = w.projected_speed / w.spin_scale;
        w.spin = stored(ratio);
        w.phase = stored(ratio * stored(.004973592) + w.phase);
      }
    }
    call("engine");
    return finish("alternate");
  }
  call("prepare_vehicle");
  s.turning_radius_y =
      s.angular_velocity[1] == 0
          ? 4000000
          : stored(s.linear_velocity[2] / (s.angular_velocity[1] * stored(6.2831855)));
  s.turning_radius_x =
      s.angular_velocity[0] == 0
          ? 4000000
          : stored(s.linear_velocity[2] / (s.angular_velocity[0] * stored(6.2831855)));
  const double x = s.local_linear[0], z = s.local_linear[2];
  s.speed = stored(std::sqrt(x * x + z * z));
  if (z < 0)
    s.speed = -s.speed;
  s.secondary_angle = stored(std::atan2(x, std::abs(z)) * .15915493667125702);
  call("predict_support");
  call("support_bookkeeping");
  if (s.tilted || s.attitude < stored(.85)) {
    for (auto &w : s.wheels)
      if (!w.contact || w.force[1] == 0)
        w.force = {};
    call("tilted_motion");
    call("refresh_motion");
    project();
    tail();
    return finish("tilted");
  }
  if (s.flags & 0x202) {
    call("flagged_motion");
    return finish("flagged");
  }
  int contacts = 0;
  for (const auto &w : s.wheels)
    contacts += w.contact;
  if (contacts < 2) {
    for (auto &w : s.wheels)
      w.force = {};
    call("body_forces");
    s.local_acceleration = {0, stored(-s.gravity_force * s.inverse_mass), 0};
    s.linear_acceleration = transform_update_vector(s.local_acceleration, s.to_world);
    call("linear_update");
    call("body_moment_inputs");
    double moment = 0;
    if (call("airborne_mode")) {
      for (auto &v : s.local_angular)
        v = stored(v * stored(.995));
    } else
      moment = stored(((2 * s.front_lever * s.front_moment - 2 * s.rear_lever * s.rear_moment) +
                       s.body_moment) *
                      s.angular_scale * stored(.15915494));
    s.local_angular_acceleration = {moment, 0, 0};
    angular_world();
    s.angular_velocity = increment(s.angular_velocity, s.angular_acceleration);
    call("refresh_motion");
    tail();
    return finish("low_support");
  }
  s.local_acceleration = transform_update_vector(s.linear_acceleration, s.to_local);
  const auto extra = transform_update_vector(s.extra_acceleration, s.to_local);
  for (int i = 0; i < 3; ++i)
    s.local_acceleration[i] = stored(s.local_acceleration[i] + extra[i]);
  call("normal_loads");
  const int environment = s.environment_mode;
  const double speed = std::abs(s.speed);
  for (int i = 0; i < 4; ++i) {
    auto &w = s.wheels[i];
    w.surface_class = w.surface_record ? *w.surface_record & 31 : s.fallback_surface;
    if ((s.flags & 0x200) || call("global_mode")) {
      w.primary_coefficient = w.base_grip;
      w.secondary_coefficient = stored(w.base_grip * stored(.8));
      continue;
    }
    double low, high;
    if (environment == 2) {
      low = .01;
      high = .2;
    } else if (environment == 1 || w.surface_class == 6 || w.surface_class == 20) {
      low = .55;
      high = w.wear_mode == 1 ? .95 : .7;
    } else {
      low = .7;
      high = 1.05;
    }
    double factor = std::clamp(stored(stored(high) - (speed - stored(13.889)) * stored(.0045)),
                               stored(low), stored(high));
    factor = stored(factor * w.base_grip);
    if (w.tire_type == 5 && w.surface_class != 1 && w.surface_class != 10)
      factor = stored(factor * .25);
    factor = stored(std::clamp(w.quality, stored(.95), stored(1.05)) * factor);
    const double axle = i < 2 ? s.front_grip_gate : s.rear_grip_gate;
    bool boost = false;
    if (axle > stored(.1))
      boost = call("grip_observation", i) < stored(.7) && environment == 0;
    if (boost || s.grip_boost)
      factor = stored(factor * stored(1.05));
    const double primary = factor * s.surface_coefficients[w.surface_class];
    w.primary_coefficient = stored(primary);
    w.secondary_coefficient = stored(primary * stored(.8));
    const double mismatch = std::abs(stored(w.spin_scale * w.spin - w.projected_speed));
    const double reduced =
        stored(std::exp((mismatch + std::abs(w.local_lateral)) * stored(-.016666668)) *
               w.primary_coefficient);
    const double floor = stored(w.primary_coefficient * .5);
    w.secondary_coefficient = std::min(w.secondary_coefficient, std::max(reduced, floor));
  }
  if (!call("vehicle_gate")) {
    s.local_linear = {};
    s.local_acceleration = {};
    s.local_angular = {};
    s.local_angular_acceleration = {};
  } else
    project();
  s.local_angular = transform_update_vector(s.angular_velocity, s.to_local);
  for (const auto *stage : {"project_wheels", "control_update", "body_moment_inputs", "body_forces"})
    call(stage);
  const auto acceleration = transform_update_vector(s.linear_acceleration, s.to_local);
  s.local_acceleration = {acceleration[0], 0, acceleration[2]};
  for (const auto *stage : {"load_transfer", "suspension_loads", "resistance", "engine", "brakes",
                            "tires", "wheel_correction"})
    call(stage);
  if (call("vehicle_gate")) {
    call("wheel_spin");
    call("combined_slip");
  }
  for (auto &w : s.wheels)
    if (w.clear_threshold < -w.clear_reference)
      w.force = {};
  if (!s.orientation_disabled)
    call("force_orientation");
  call("body_moments");
  // Original accumulation order is rear-right, rear-left, front-left, front-right.
  const auto sum = [&](int component) {
    return ((s.wheels[2].force[component] + s.wheels[3].force[component]) +
            s.wheels[1].force[component]) +
           s.wheels[0].force[component];
  };
  if (sum(1) * stored(.101936795) <= 0)
    s.local_acceleration = {s.lateral_contribution, stored(-s.inverse_mass * s.gravity_force),
                            stored(s.inverse_mass * s.longitudinal_contribution)};
  else
    s.local_acceleration = {
        stored((sum(0) + s.lateral_contribution) * s.inverse_mass * stored(1.1)),
        stored(-s.inverse_mass * s.gravity_force),
        stored((sum(2) + s.longitudinal_contribution) * s.inverse_mass)};
  angular_world();
  s.angular_velocity = transform_update_vector(s.local_angular, s.to_world);
  s.angular_velocity = increment(s.angular_velocity, s.angular_acceleration);
  if (std::abs(s.local_acceleration[0]) < stored(.001))
    s.local_acceleration[0] = 0;
  s.linear_acceleration = transform_update_vector(s.local_acceleration, s.to_world);
  call("linear_update");
  if (s.support_count > 2 && std::abs(s.speed) < 6) {
    auto angular = transform_update_vector(s.angular_velocity, s.to_local);
    if (std::abs(angular[1]) < stored(.0027777778))
      angular[1] = 0;
    s.angular_velocity = transform_update_vector(angular, s.to_world);
  }
  tail();
  return finish("supported");
}
} // namespace mco
