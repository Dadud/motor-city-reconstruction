#pragma once
#include <array>
namespace mco {
struct MomentWheel {
    double lateral_force, longitudinal_force, secondary_response, support_correction;
    bool contact;
};
struct BodyMomentState {
    std::array<MomentWheel,4> wheels;
    double speed, front_lever, rear_lever, front_track, rear_track, height_parameter, mass_parameter;
    double inverse_pitch, inverse_yaw, inverse_roll, pitch_multiplier;
    double front_vertical, rear_vertical, yaw_contribution;
    bool alternate_mode;
};
std::array<double,3> accumulate_body_moments(BodyMomentState state);
}
