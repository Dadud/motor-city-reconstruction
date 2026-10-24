#pragma once
#include "mco/track_surface_world.hpp"
#include <array>
#include <cstddef>
#include <span>
#include <optional>

namespace mco {
struct TrackPlane {
  std::array<float, 3> reference{};
  std::array<float, 3> normal{};
  bool normal_written = false;
};

// Triangle mode reconstructs the original normalized plane. Row mode copies
// the selected path point and leaves the caller's normal bytes untouched.
TrackPlane track_plane_from_query(const TrackSurfaceWorld &world,
                                  std::span<const std::byte, 68> query,
                                  std::array<float, 3> normal_seed,
                                  std::optional<std::array<float, 3>> query_point = std::nullopt);

// Bounded 0x42e010 composition. normal_seed makes the original row-mode
// uninitialized stack input explicit; no guessed normal is substituted.
bool sample_track_surface(const TrackSurfaceWorld &world,
                         std::span<std::byte, 68> query,
                         std::array<float, 3> &point,
                         std::int32_t track_index,
                         std::array<float, 3> normal_seed);
}
