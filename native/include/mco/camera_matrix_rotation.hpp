#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
namespace mco {
// Original 0x6f1780, 0x6f1850, 0x6f1910; Rotate a nine-float matrix about the selected original axis using turn-based angles.
void camera_matrix_rotation(std::span<const float,9> source, float turns, std::span<float,9> destination, std::uint32_t axis);
}
