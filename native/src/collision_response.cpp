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
float rounded(double value, bool allow_nonfinite) {
    return allow_nonfinite ? static_cast<float>(value) : stored(value);
}
} // namespace

TangentialResponse tangential_response(const std::array<double, 3>& relative_vector,
                                      const std::array<double, 3>& normal_input,
                                      double threshold_coefficient,
                                      double sliding_coefficient,
                                      bool allow_nonfinite) {
    std::array<double, 3> vector{}, normal{}, remainder{};
    for (std::size_t i = 0; i < 3; ++i) {
        vector[i] = rounded(relative_vector[i], allow_nonfinite);
        normal[i] = rounded(normal_input[i], allow_nonfinite);
    }
    const double threshold = rounded(threshold_coefficient, allow_nonfinite),
                 sliding = rounded(sliding_coefficient, allow_nonfinite);
    const double extended = -((vector[0]*normal[0]+vector[1]*normal[1])+vector[2]*normal[2]);
    const double approach = rounded(extended, allow_nonfinite);
    if (extended <= 0) return {0, {0,0,0}};
    for (std::size_t i = 0; i < 3; ++i)
        remainder[i] = rounded(vector[i]-rounded(approach*normal[i], allow_nonfinite),
                               allow_nonfinite);
    const double squared = remainder[0]*remainder[0]+(remainder[1]*remainder[1]+remainder[2]*remainder[2]);
    const double length_extended = std::sqrt(squared),
                 length = rounded(length_extended, allow_nonfinite);
    std::array<float,3> direction{};
    if (squared == 0) return {0,{0,0,0}};
    const double inverse_length = 1.0/length_extended;
    for (std::size_t i = 0; i < 3; ++i)
        direction[i] = -rounded(remainder[i]*inverse_length, allow_nonfinite);
    if (length <= 0) return {0,direction};
    const bool sliding_branch = threshold*approach < length;
    const double scale = sliding_branch ? rounded(sliding*approach, allow_nonfinite) : length;
    for (auto& value : direction) value = rounded(static_cast<double>(value)*scale,
                                                  allow_nonfinite);
    return {sliding_branch ? 2 : 1, direction};
}
} // namespace mco
