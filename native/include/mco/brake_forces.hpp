#pragma once
#include "mco/brake_thermal.hpp"
#include <vector>
#include <utility>
namespace mco {
struct BrakeForceWheel {
    double spin_value,spin_adjustment,spin_scale,projected_speed,normal_load,longitudinal_force,control_angle;
    std::int32_t component_code;
    double inertia_addend,inertia_multiplier;
};
struct BrakeForceState {
    BrakeThermalState thermal;
    std::array<BrakeForceWheel,4> wheels;
    double front_quality,rear_quality,front_gate;
    std::int32_t rear_gate;
    double rear_distribution,drive_factor,pitch_angle;
    std::int32_t vehicle_code;
    bool auxiliary_flag;
    std::int32_t parking_ramp;
};
struct BrakeEvent {
    int kind; // 0: wear, 1: controller
    int slot;
    double value;
};
struct BrakeForceOutput {
    BrakeForceState state;
    std::vector<std::pair<int,double>> wear_events;
    std::vector<int> controller_events;
    std::vector<BrakeEvent> events;
};
BrakeForceOutput update_brake_forces(BrakeForceState state);
}
