#pragma once
#include <array>
namespace mco {
struct WheelSpeedInput { double angle; bool contact; double spin_value; double spin_scale; };
struct WheelSpeedState {
    std::array<WheelSpeedInput, 4> wheels; // Consecutive native slots, not load-module rear order.
    double lateral_velocity, longitudinal_velocity, yaw_rate_turns;
    double front_offset, rear_offset, front_track, rear_track;
};
std::array<float, 4> project_wheel_speeds(const WheelSpeedState& state);
}
