#include "mco/vehicle_update.hpp"
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>
#include <stdexcept>
int main() {
  mco::VehicleUpdateState s;
  bool rejected = false;
  try {
    mco::update_vehicle(s, {});
  } catch (const std::invalid_argument &) {
    rejected = true;
  }
  assert(rejected);
  s.active = false;
  auto out = mco::update_vehicle(s, [](const auto &, auto &) { return 0.; });
  assert(out.branch == "inactive" && out.calls.size() == 1);
  s.active = true;
  s.wheels[0].contact = s.wheels[1].contact = true;
  out = mco::update_vehicle(s, [](const auto &call, auto &state) {
    if (call.stage == "predict_support")
      state.attitude = .7;
    return 0.;
  });
  assert(out.branch == "tilted");
  s.attitude = 1;
  out = mco::update_vehicle(s, [](const auto &call, auto &state) {
    if (call.stage == "predict_support")
      for (auto &w : state.wheels)
        w.contact = false;
    return 0.;
  });
  assert(out.branch == "low_support");
  out = mco::update_vehicle(s, [](const auto &call, auto &state) {
    if (call.stage == "body_moments")
      state.local_angular_acceleration = {.03, .04, -.05};
    return call.stage == "vehicle_gate" ? 1. : 0.;
  });
  assert(out.branch == "supported" && out.state.angular_acceleration[2] < 0);
  out = mco::update_vehicle(s, [](const auto &call, auto &state) {
    if (call.stage == "prepare_vehicle")
      state.attitude = .849999999;
    return 0.;
  });
  assert(out.branch == "supported"); // Child write rounds to float32 0.85.
  s.linear_velocity = {1, 2, 3};
  s.linear_acceleration = {32, -32, 0};
  mco::apply_linear_update(s, true);
  assert((s.linear_velocity == mco::UpdateVector{2, 1, 3}));
  mco::apply_linear_update(s, false);
  assert((s.linear_velocity == mco::UpdateVector{0, 1, 0}) &&
         (s.linear_acceleration == mco::UpdateVector{}));
}
