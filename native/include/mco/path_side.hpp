#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
namespace mco {
// Original 0x42ee50; Track path query preserving original float-store and strict-comparison ordering.
std::uint32_t path_side(std::span<const std::array<float,3>> points, std::span<const float,3> position, std::uint32_t index);
}
