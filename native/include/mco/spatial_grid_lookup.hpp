#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
#include "mco/spatial_query_memory.hpp"
namespace mco {
// Original 0x552880; Resolve a grid/quadtree leaf using original rounded X/Z coordinates and child ordering.
std::uint32_t spatial_grid_lookup(const SpatialQueryMemory &memory, std::span<const float,3> position, std::span<const float,2> origin, std::span<const float,2> scale);
}
