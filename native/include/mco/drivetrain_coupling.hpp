#pragma once
#include <cstdint>
namespace mco {
struct DrivetrainCoupling {
    std::int32_t rpm;
    float curve_torque, effective_torque, drag_factor, drag_speed;
    std::int32_t gear_index;
    float engagement, coupling_resistance, environment_field;
    bool environment_override, environment_selector_enabled;
    std::int32_t environment_selector;
};
struct DrivetrainCouplingOutput {
    float power, drag, corrected_torque, acceleration_input, environment_correction;
};
float environment_correction(float field, bool override_mode, bool selector_enabled, std::int32_t selector);
DrivetrainCouplingOutput couple_drivetrain(const DrivetrainCoupling& state);
}
