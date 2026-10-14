#pragma once

#include <array>
#include <cstdint>

namespace mco {
struct ResistanceWheel {
    double slip_angle;
    std::uint32_t surface_id;
    double normal_load;
    double rolling_speed;
    double speed_scale;
    bool contact;
    double longitudinal_force;
};
struct ResistanceResult {
    std::array<ResistanceWheel, 4> wheels;
    float last_contribution;
};

// Bounded 0x53e3d0: mode predicate is explicitly supplied, body_angle is turns.
// Returns the final wheel contribution, independently of whether it was applied.
ResistanceResult rolling_resistance(std::array<ResistanceWheel, 4> wheels,
    double speed, double front_coefficient, double rear_coefficient,
    double front_adjustment, double rear_adjustment, double body_angle,
    bool disabled_flag = false, bool mode_predicate = false, bool alternate = false);
} // namespace mco
