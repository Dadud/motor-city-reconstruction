#pragma once
#include <array>
namespace mco {
struct BodyResistanceState {
    double speed,longitudinal_speed,drag_parameter;
    bool accessory_parameter,accessory_enabled;
    double drag_adjustment;
    int vehicle_code;
    double secondary_angle,area_parameter,density,wind_lateral,wind_longitudinal,drafting_factor;
    bool resistance_disabled;
    double pitch_angle,length_parameter,height_parameter;
    bool load_transfer_disabled;
    double front_lever,rear_lever,downforce_parameter,configuration_downforce;
    std::array<double,4> wheel_loads;
    std::array<bool,4> contacts;
};
struct BodyResistanceOutput {
    double longitudinal_drag,yaw_contribution,pitch_contribution;
    std::array<double,4> wheel_loads;
};
BodyResistanceOutput calculate_body_resistance(BodyResistanceState state);
}
