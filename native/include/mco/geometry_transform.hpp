#pragma once
#include <array>

namespace mco {
std::array<float,66> transform_world_vertices_22(
    const std::array<float,66>& local_vertices,
    const std::array<float,9>& matrix,
    const std::array<float,3>& position) noexcept;
}
