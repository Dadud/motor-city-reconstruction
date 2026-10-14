#pragma once
#include <array>
#include <vector>
#include <utility>
#include <cstdint>
namespace mco {
struct SpinWheel {
    double spin_value,spin_adjustment,spin_scale,projected_speed,normal_load,kinetic_parameter,ratio_denominator,phase;
    bool correction_enabled,contact;
    double secondary_angle=0,slip_ratio=0,kinetic_value=0,local_lateral=0,local_vertical=0,local_longitudinal=0;
};
struct WheelSpinState {
    std::array<SpinWheel,4> wheels;
    std::uint8_t direction_mode;
    bool override_control;
    std::int32_t rpm;
    double gear_multiplier,front_scale,rear_scale,front_compliance,rear_compliance;
    double front_secondary_angle,rear_secondary_angle,front_quality,rear_quality,body_secondary_angle;
    double front_lever,rear_lever,yaw_rate,lateral_velocity;
};
struct WheelSpinOutput {WheelSpinState state;std::vector<std::pair<int,double>> wear_events;};
WheelSpinOutput integrate_wheel_spin(WheelSpinState state);
}
