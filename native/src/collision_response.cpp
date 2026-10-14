#include "mco/collision_response.hpp"
#include <cmath>
#include <limits>
#include <stdexcept>

namespace mco {
namespace {
float stored(double value) {
    if (!std::isfinite(value) || std::abs(value) > std::numeric_limits<float>::max())
        throw std::invalid_argument("finite float32 collision value required");
    return static_cast<float>(value);
}
} // namespace

TangentialResponse tangential_response(const std::array<double, 3>& relative_vector,
                                      const std::array<double, 3>& normal_input,
                                      double threshold_coefficient,
                                      double sliding_coefficient) {
    std::array<double, 3> vector{}, normal{}, remainder{};
    for (std::size_t i = 0; i < 3; ++i) {
        vector[i] = stored(relative_vector[i]); normal[i] = stored(normal_input[i]);
    }
    const double threshold = stored(threshold_coefficient), sliding = stored(sliding_coefficient);
    const double extended = -((vector[0]*normal[0]+vector[1]*normal[1])+vector[2]*normal[2]);
    const double approach = stored(extended);
    if (extended <= 0) return {0, {0,0,0}};
    for (std::size_t i = 0; i < 3; ++i) remainder[i] = stored(vector[i]-stored(approach*normal[i]));
    const double squared = remainder[0]*remainder[0]+(remainder[1]*remainder[1]+remainder[2]*remainder[2]);
    const double length_extended = std::sqrt(squared), length = stored(length_extended);
    std::array<float,3> direction{};
    if (squared == 0) return {0,{0,0,0}};
    const double inverse_length = 1.0/length_extended;
    for (std::size_t i = 0; i < 3; ++i) direction[i] = -stored(remainder[i]*inverse_length);
    if (length <= 0) return {0,direction};
    const bool sliding_branch = threshold*approach < length;
    const double scale = sliding_branch ? stored(sliding*approach) : length;
    for (auto& value : direction) value = stored(static_cast<double>(value)*scale);
    return {sliding_branch ? 2 : 1, direction};
}
} // namespace mco
