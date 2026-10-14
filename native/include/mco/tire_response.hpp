#pragma once

#include <array>

namespace mco {
using WheelResponseTable = std::array<double, 26>;
struct WheelCurveInput {
    double slip_angle;
    double secondary_angle;
    double normal_load;
    double surface_multiplier;
};

// Bounded consumers 0x53f630/0x53f830. Tables remain caller supplied.
// Negative loads and non-finite / float32-overflowing inputs are rejected.
float wheel_response(const WheelResponseTable& table, double angle_coefficient,
                     const WheelCurveInput& wheel, bool secondary = false,
                     bool alternate_load = false);
} // namespace mco
