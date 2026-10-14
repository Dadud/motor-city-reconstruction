#pragma once
#include <array>
#include <cstdint>
namespace mco {
struct SuspensionLoadInput {
    std::array<double, 4> loads; // LF RF LR RR.
    std::array<bool, 4> support;
    double attitude;
    bool enabled;
    double speed, bank_angle, pitch_angle, mass, mass_offset;
    double front_weight_parameter, rear_weight_parameter, front_lever, rear_lever;
    double wheelbase, rear_track, gear_factor, torque;
    std::int32_t component_mode;
    bool disable_torque;
};
std::array<float, 4> correct_suspension_load(const SuspensionLoadInput& state);
}
