#pragma once
#include <array>
#include <cstdint>

namespace mco {
// Inputs observed by original 0x536fb0. Counter, track and mode producers are external.
struct WindState {
    std::int32_t simulation_counter;
    std::int32_t weather_seed;
    std::array<double,3> track_direction;
    std::array<double,9> world_to_body;
    bool disabled=false;
};
struct WindOutput {
    std::array<double,3> body_velocity;
    bool present;
};
WindOutput calculate_wind(WindState state);
}
