#include "mco/vehicle_update.hpp"
#include <iomanip>
#include <iostream>
#include <map>
#include <string>
#include <vector>
namespace {
std::vector<double *> numbers(mco::VehicleUpdateState &s) {
  std::vector<double *> a{&s.attitude,
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
                          &s.rear_grip_gate};
  for (auto *v : {&s.linear_velocity, &s.angular_velocity, &s.linear_acceleration,
                  &s.angular_acceleration, &s.extra_acceleration, &s.local_linear, &s.local_angular,
                  &s.local_acceleration, &s.local_angular_acceleration})
    for (auto &x : *v)
      a.push_back(&x);
  for (auto *v : {&s.to_local, &s.to_world})
    for (auto &x : *v)
      a.push_back(&x);
  for (auto &x : s.surface_coefficients)
    a.push_back(&x);
  for (auto &w : s.wheels) {
    for (auto *x : {&w.primary_coefficient, &w.secondary_coefficient, &w.base_grip, &w.quality,
                    &w.spin_scale, &w.spin, &w.projected_speed, &w.local_lateral, &w.phase,
                    &w.primary_angle, &w.clear_reference, &w.clear_threshold})
      a.push_back(x);
    for (auto &x : w.force)
      a.push_back(&x);
  }
  return a;
}
struct Mutation {
  std::string stage, name;
  std::vector<double> values;
};
} // namespace
int main() {
  std::cout << std::setprecision(17);
  for (int run = 0; run < 100000; ++run) {
    mco::VehicleUpdateState s;
    int active, tilted, disabled, boost;
    if (!(std::cin >> active))
      return std::cin.eof() ? 0 : 2;
    if (!(std::cin >> tilted >> s.flags >> s.environment_mode >> s.fallback_surface >>
          s.support_count >> disabled >> boost))
      return 2;
    s.active = active;
    s.tilted = tilted;
    s.orientation_disabled = disabled;
    s.grip_boost = boost;
    for (auto &w : s.wheels) {
      int contact, surface;
      if (!(std::cin >> contact >> surface >> w.surface_class >> w.wear_mode >> w.tire_type))
        return 2;
      w.contact = contact;
      if (surface >= 0)
        w.surface_record = static_cast<std::uint8_t>(surface);
    }
    for (auto *v : numbers(s))
      if (!(std::cin >> *v))
        return 2;
    int query_count;
    std::cin >> query_count;
    std::map<std::string, std::vector<double>> queries;
    for (int i = 0; i < query_count; ++i) {
      std::string name;
      int n;
      std::cin >> name >> n;
      auto &values = queries[name];
      values.resize(n);
      for (auto &v : values)
        std::cin >> v;
    }
    int mutation_count;
    std::cin >> mutation_count;
    std::vector<Mutation> mutations;
    for (int i = 0; i < mutation_count; ++i) {
      Mutation m;
      int n;
      std::cin >> m.stage >> m.name >> n;
      m.values.resize(n);
      for (auto &v : m.values)
        std::cin >> v;
      mutations.push_back(m);
    }
    if (!std::cin)
      return 2;
    std::map<std::string, std::size_t> counts;
    auto out =
        mco::update_vehicle(s, [&](const mco::UpdateCall &c, mco::VehicleUpdateState &state) {
          for (const auto &m : mutations)
            if (m.stage == c.stage) {
              if (m.name == "contacts") {
                int mask = static_cast<int>(m.values.at(0));
                for (int i = 0; i < 4; ++i)
                  state.wheels[i].contact = mask & (1 << i);
              } else if (m.name == "forces") {
                for (int i = 0; i < 4; ++i)
                  for (int j = 0; j < 3; ++j)
                    state.wheels[i].force[j] = m.values.at(i * 3 + j);
              } else if (m.name == "attitude")
                state.attitude = m.values.at(0);
              else if (m.name == "local_angular_acceleration" || m.name == "linear_velocity") {
                auto &v = m.name == "linear_velocity" ? state.linear_velocity
                                                      : state.local_angular_acceleration;
                for (int j = 0; j < 3; ++j)
                  v[j] = m.values.at(j);
              } else
                throw std::invalid_argument("unsupported supplied mutation");
            }
          if (c.stage == "linear_update" && queries.contains("execute_linear") &&
              queries.at("execute_linear").at(0))
            mco::apply_linear_update(state, queries.at("linear_gate").at(0) != 0);
          auto it = queries.find(c.stage);
          if (it == queries.end())
            return 0.;
          auto &values = it->second;
          return values.at(values.size() == 1 ? 0 : counts[c.stage]++);
        });
    std::cout << out.branch << ' ' << out.state.active << ' ' << out.state.tilted << ' '
              << out.state.flags << ' ' << out.state.environment_mode << ' '
              << out.state.fallback_surface << ' ' << out.state.support_count << ' '
              << out.state.orientation_disabled << ' ' << out.state.grip_boost;
    for (const auto &w : out.state.wheels)
      std::cout << ' ' << w.contact << ' '
                << (w.surface_record ? static_cast<int>(*w.surface_record) : -1) << ' '
                << w.surface_class << ' ' << w.wear_mode << ' ' << w.tire_type;
    for (const auto *v : numbers(out.state))
      std::cout << ' ' << *v;
    std::cout << ' ' << out.calls.size();
    for (const auto &c : out.calls)
      std::cout << ' ' << c.stage << ' ' << c.slot.value_or(-1);
    std::cout << '\n';
  }
  return 2;
}
