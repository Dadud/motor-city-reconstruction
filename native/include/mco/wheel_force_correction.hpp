#pragma once
#include <array>
#include <cstdint>

namespace mco {
struct ForceCorrectionWheel {
    double projected_speed, spin_value, spin_adjustment, spin_scale;
    double lateral_force, longitudinal_force, normal_load;
    double primary_coefficient, secondary_coefficient;
    bool contact, correction_enabled;
};
std::array<ForceCorrectionWheel,4> correct_wheel_forces(
    std::array<ForceCorrectionWheel,4> wheels, double service_control,
    double other_control, bool parking_control, std::uint8_t direction_mode,
    bool override_control);
}
