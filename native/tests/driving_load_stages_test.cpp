#include "mco/driving_load_stages.hpp"
#include <stdexcept>

namespace {
void check(bool value, const char *message) {
  if (!value)
    throw std::runtime_error(message);
}
}

int main() {
  mco::DrivingLoadParameters p{.03, .06, 1300, 2.7, 1.6, 1.7, .7, .12, .18,
                               {9.8, 10, 9.5, 9.9}, -.03, 100, .45, .55,
                               -2.3, 400, .07, 0};
  mco::VehicleUpdateState state{};
  state.speed = 20;
  state.turning_radius_y = -40;
  state.local_acceleration = {3, 2, 1};
  state.front_lever = 1.2;
  state.rear_lever = 1.5;
  state.support_count = 4;
  for (auto &wheel : state.wheels)
    wheel.contact = true;

  int delegated = 0;
  const auto executor = mco::make_driving_load_executor(
      p, [&](const mco::UpdateCall &, mco::VehicleUpdateState &) {
        ++delegated;
        return 0.0;
      });
  executor({"normal_loads", {}}, state);
  for (const auto &wheel : state.wheels)
    check(wheel.force[1] > 0 && wheel.force[0] == 0 && wheel.force[2] == 0,
          "initial load stage must write complete force vectors");

  for (std::size_t i = 0; i < state.wheels.size(); ++i)
    state.wheels[i].force = {10.0 + i, state.wheels[i].force[1], 20.0 + i};
  const auto before_transfer = state.wheels;
  executor({"load_transfer", {}}, state);
  bool transfer_changed = false;
  for (std::size_t i = 0; i < state.wheels.size(); ++i) {
    check(state.wheels[i].force[0] == before_transfer[i].force[0] &&
              state.wheels[i].force[2] == before_transfer[i].force[2],
          "load transfer must preserve non-load force components");
    transfer_changed |= state.wheels[i].force[1] != before_transfer[i].force[1];
  }
  check(transfer_changed, "load transfer stage did not update normal loads");

  const auto before_suspension = state.wheels;
  executor({"suspension_loads", {}}, state);
  bool suspension_changed = false;
  for (std::size_t i = 0; i < state.wheels.size(); ++i) {
    check(state.wheels[i].force[0] == before_suspension[i].force[0] &&
              state.wheels[i].force[2] == before_suspension[i].force[2],
          "suspension load stage must preserve non-load force components");
    suspension_changed |= state.wheels[i].force[1] != before_suspension[i].force[1];
  }
  check(suspension_changed, "suspension load stage did not update normal loads");

  executor({"engine", {}}, state);
  check(delegated == 1, "unrecovered stages must reach the supplied executor");
  const auto incomplete = mco::make_driving_load_executor(p, {});
  bool rejected = false;
  try {
    incomplete({"engine", {}}, state);
  } catch (const std::invalid_argument &) {
    rejected = true;
  }
  check(rejected, "missing executor for unrecovered stages must remain explicit");
}
