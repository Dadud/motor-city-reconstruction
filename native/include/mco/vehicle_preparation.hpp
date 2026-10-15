#pragma once
#include <array>
#include <cstdint>
namespace mco {
inline constexpr std::array<double,9> preparation_identity{1,0,0,0,1,0,0,0,1};
struct PreparationState {
    double local_vertical_acceleration=0,front_observation=0,rear_observation=0,front_factor=0,rear_factor=0;
    int support_count=0;
    double pitch_extent=0,roll_extent=0,pitch_limit=.1,roll_limit=.1,orientation_scale=1;
    double pitch_reference=0,roll_reference=0,minimum_pitch=.1,maximum_pitch=.1,maximum_roll=.1;
    double pitch_offset=0,pitch=0,roll=0,extent=0;
    std::array<double,3> source_vector{};
    std::array<double,9> source_matrix=preparation_identity,motion_matrix=preparation_identity;
    double damping=0,pitch_target=0,roll_target=0;
    std::array<double,3> angle_delta{};
    std::array<double,6> auxiliary{};
    std::array<double,9> to_world=preparation_identity,to_local=preparation_identity;
};
PreparationState prepare_vehicle(PreparationState state);
struct SupportWheel {
    bool contact;
    double bound_parameter,amplitude,frequency,displacement=0,correction=0;
};
struct SupportState {
    std::array<SupportWheel,4> wheels;
    double phase,local_longitudinal_speed;
    std::array<std::uint8_t,256> noise;
};
SupportState update_support_disturbance(SupportState state);
}
