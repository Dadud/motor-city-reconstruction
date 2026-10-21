#pragma once
#include <array>
#include <cstdint>

namespace mco {
std::array<std::uint32_t, 9> transpose_3x3_words(
    const std::array<std::uint32_t, 9>& values) noexcept;
float dot_3_f32(const std::array<float, 3>& left,
                const std::array<float, 3>& right) noexcept;
std::array<float, 9> integrate_rotation_matrix(
    const std::array<float, 9>& matrix,
    const std::array<float, 3>& delta_turns) noexcept;
std::array<float, 9> multiply_3x3(
    const std::array<float, 9>& matrix_a,
    const std::array<float, 9>& matrix_b) noexcept;
std::array<float, 9> repair_rotation_matrix(
    const std::array<float, 9>& matrix, int iterations = 10);
}
