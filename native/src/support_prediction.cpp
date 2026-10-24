#include "mco/support_prediction.hpp"
#include <cmath>
#include <limits>
#include <stdexcept>

namespace mco {
namespace {
double f32(double value) {
  if (!std::isfinite(value) || std::abs(value) > std::numeric_limits<float>::max())
    throw std::invalid_argument("finite binary32 support value required");
  return static_cast<float>(value);
}
void normalize(SupportVector &value) {
  for (auto &component : value) component = f32(component);
}
void validate_record(const SupportRecord &record) {
  if (record.surface_id.has_value() != record.surface_code.has_value())
    throw std::invalid_argument("surface identity and descriptor must be supplied together");
}
}

SupportPredictionOutput predict_support(SupportPredictionState state,
                                         const SupportProjector &project) {
  if (!project) throw std::invalid_argument("terrain projection executor required");
  if (state.fallback_surface > 31)
    throw std::invalid_argument("fallback surface outside five-bit domain");
  normalize(state.position);
  normalize(state.velocity);
  for (auto &component : state.to_world) component = f32(component);
  for (auto &wheel : state.wheels) {
    normalize(wheel.local_point);
    normalize(wheel.world_point);
    wheel.clear_reference = f32(wheel.clear_reference);
    if (wheel.clear_reference < 0)
      throw std::invalid_argument("nonnegative contact reference required");
    validate_record(wheel.record);
  }

  SupportVector lookahead{};
  const double step = f32(1.0 / 48.0);
  for (std::size_t i = 0; i < 3; ++i)
    lookahead[i] = f32(state.position[i] + f32(state.velocity[i] * step));

  std::vector<SupportQuery> queries;
  queries.reserve(state.wheels.size());
  std::int32_t support_count = 0;
  for (std::size_t slot = 0; slot < state.wheels.size(); ++slot) {
    auto &wheel = state.wheels[slot];
    SupportVector point{};
    for (std::size_t i = 0; i < 3; ++i) {
      const double x = f32(wheel.local_point[0] * state.to_world[i]);
      const double y = f32(wheel.local_point[1] * state.to_world[3 + i]);
      const double z = f32(wheel.local_point[2] * state.to_world[6 + i]);
      point[i] = f32(f32(f32(x + y) + z) + lookahead[i]);
    }
    SupportQuery query{static_cast<std::uint32_t>(slot), point, wheel.world_point, state.context};
    queries.push_back(query);
    auto projection = project(query);
    normalize(projection.point);
    normalize(projection.reference_position);
    validate_record(projection.record);
    wheel.support_delta = f32(projection.point[1] - projection.reference_position[1]);
    wheel.contact = wheel.support_delta >= -wheel.clear_reference;
    support_count += wheel.contact ? 1 : 0;
    wheel.surface_class = projection.record.surface_id
                              ? static_cast<std::uint32_t>(*projection.record.surface_code & 31)
                              : state.fallback_surface;
    wheel.world_point = projection.point;
    wheel.record = projection.record;
  }
  state.support_count = support_count;
  return {std::move(state), std::move(queries)};
}
}
