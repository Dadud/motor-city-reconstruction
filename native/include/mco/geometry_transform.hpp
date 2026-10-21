#pragma once
#include <array>

namespace mco {
std::array<float,66> transform_world_vertices_22(
    const std::array<float,66>& local_vertices,
    const std::array<float,9>& matrix,
    const std::array<float,3>& position) noexcept;

// In-place-safe translation of contiguous three-float points (original 0x6f1450).
void add_vector_to_points(const float* source,
                          const std::array<float,3>& translation,
                          float* destination,
                          std::size_t count);
}
