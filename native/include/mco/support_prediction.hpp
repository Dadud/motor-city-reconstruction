#pragma once
#include <array>
#include <cstdint>
#include <functional>
#include <optional>
#include <vector>

namespace mco {
using SupportVector = std::array<double, 3>;
using SupportMatrix = std::array<double, 9>;
struct SupportRecord {
  std::int32_t sector = 0, group = 0;
  std::uint32_t status = 0;
  std::optional<std::uint32_t> surface_id;
  std::array<std::optional<std::uint32_t>, 4> vertex_ids{};
  std::optional<std::uint8_t> surface_code;
};
struct PredictionWheel {
  SupportVector local_point{}, world_point{};
  double clear_reference = 0, support_delta = 0;
  SupportRecord record{};
  bool contact = false;
  std::uint32_t surface_class = 0;
};
struct SupportPredictionState {
  std::array<PredictionWheel, 4> wheels{};
  SupportVector position{}, velocity{};
  SupportMatrix to_world{1, 0, 0, 0, 1, 0, 0, 0, 1};
  std::int32_t context = 0;
  std::uint32_t fallback_surface = 0;
  std::int32_t support_count = 0;
};
struct SupportQuery {
  std::uint32_t slot = 0;
  SupportVector point{}, previous_world{};
  std::int32_t context = 0;
};
struct SupportProjection {
  SupportVector point{}, reference_position{};
  SupportRecord record{};
};
using SupportProjector = std::function<SupportProjection(const SupportQuery &)>;
struct SupportPredictionOutput {
  SupportPredictionState state;
  std::vector<SupportQuery> queries;
};

// Recovered original 0x53d320. Terrain projection and its aliased record writes
// remain an explicit caller-supplied operation.
SupportPredictionOutput predict_support(SupportPredictionState state,
                                         const SupportProjector &project);
}
