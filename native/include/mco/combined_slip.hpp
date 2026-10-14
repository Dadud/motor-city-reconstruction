#pragma once
#include <array>
#include <vector>
#include <cstdint>
namespace mco {
struct CombinedSlipWheel {
    double slip_ratio,lateral_force,longitudinal_force,secondary_response,normal_load;
    double primary_coefficient,secondary_coefficient,spin_value,spin_scale,projected_speed;
    bool contact;
    std::int32_t component_code,wear_mode;
};
struct CombinedSlipState {
    std::array<CombinedSlipWheel,4> wheels;
    double speed;
    bool parking_control,alternate_mode;
    double front_quality,rear_quality;
    std::int32_t vehicle_code;
};
struct SlipEffect {
    int operation,slot;
    double amount,parameter_a=0,parameter_b=0,parameter_c=0;
};
struct CombinedSlipOutput {CombinedSlipState state;std::vector<SlipEffect> effects;};
double longitudinal_slip_factor(double slip);
CombinedSlipOutput limit_combined_slip(CombinedSlipState state);
}
