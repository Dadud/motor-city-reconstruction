#pragma once

#include <array>

namespace mco {
struct LoadTransferInput {
    std::array<double, 4> loads; // Original processing order: LF RF LR RR.
    double attitude;
    double longitudinal_acceleration;
    double lateral_acceleration;
    double speed;
    double mass;
    double wheelbase;
    double front_track;
    double rear_track;
    double height_parameter;
    double front_offset;
    double rear_offset;
};

// Bounded 0x53e680 correction; contact and initial-load producers are external.
std::array<float, 4> transfer_load(const LoadTransferInput& state);
} // namespace mco
