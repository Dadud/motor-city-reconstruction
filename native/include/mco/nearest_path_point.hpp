#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
namespace mco {
// Original 0x42e6b0; Track path query preserving original float-store and strict-comparison ordering.
std::uint32_t nearest_path_point(std::span<const std::array<float,3>> points, std::span<const float,3> position, std::uint32_t group, std::int32_t count);
}
