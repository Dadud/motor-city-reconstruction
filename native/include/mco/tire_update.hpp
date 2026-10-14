#pragma once
#include "mco/tire_response.hpp"
#include <array>
#include <cstdint>
namespace mco {
struct TireCurves { WheelResponseTable primary, secondary; double angle_coefficient; };
struct TireWheel {
    double steering_angle, slip_angle, secondary_angle, projected_speed, normal_load;
    bool contact;
    double surface_multiplier, lateral_force, longitudinal_force, secondary_response;
};
struct TireUpdateState {
    std::array<TireWheel, 4> wheels; // Consecutive original records.
    TireCurves front_curves, rear_curves;
    std::int32_t raw_control;
    double speed, mass_parameter, front_lever, rear_lever, front_track, wheelbase, maximum_steering;
    double longitudinal_velocity, lateral_velocity, lateral_acceleration, yaw_rate, body_slip;
    bool rear_steering;
    std::array<bool, 4> mode_observations;
    bool alternate_load = false;
};
TireUpdateState update_tires(TireUpdateState state);
}
