#pragma once
#include <array>

namespace mco {
struct TangentialResponse {
    int status;
    std::array<float, 3> vector;
};
// Complete recovered 0x458390. Inputs retain producer-neutral naming.
TangentialResponse tangential_response(const std::array<double, 3>& relative_vector,
                                      const std::array<double, 3>& normal,
                                      double threshold_coefficient,
                                      double sliding_coefficient);
} // namespace mco
