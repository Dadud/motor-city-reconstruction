#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
#include "mco/track_surface_world.hpp"
namespace mco {
// Original 0x42e760; Update a track surface record through cached quad, spatial candidates and nearest-path fallback.
std::uint32_t track_surface_lookup(const TrackSurfaceWorld &world, std::span<const float,3> position, std::span<std::byte,68> record);
}
