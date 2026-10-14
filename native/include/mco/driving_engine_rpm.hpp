#pragma once
#include <cstdint>
namespace mco {
struct DrivingEngineRPM {
    std::int32_t idle_rpm, configured_max_rpm;
    float throttle, normalized_rpm;
    std::int32_t target_rpm;
    bool enabled;
    float inertia_factor, acceleration_input, angular_speed;
    std::int32_t rpm, limiter_rpm, gear_index;
    float gear_speed_factor, longitudinal_speed, acceleration_output = 0;
};
// Complete 0x546e70 helper. Caller supplies minimum separately from idle.
DrivingEngineRPM update_driving_engine_rpm(DrivingEngineRPM state, std::int32_t minimum_rpm);
}
