#pragma once
#include <array>
#include <cstdint>
#include <functional>
#include <optional>
#include <string>
#include <vector>

namespace mco {
// Observed consumer values. Defaults are research fixtures, not stock startup.
struct DriveWheel {
    double spin=0, adjustment=0, radius=.3, inertia=1, conversion=1,
           distribution=.5, torque=0, normal_load=3000, longitudinal_force=0;
    bool driven=true, contact=true;
};
struct DriveState {
    std::array<DriveWheel,4> wheels{};
    std::uint32_t engine_flags=1, vehicle_flags=4;
    std::int32_t rpm=3000, gear=2, hold_ticks=0;
    std::uint8_t override_byte=0, raw_throttle=128, auxiliary_byte=0;
    std::int32_t component_mode=0;
    std::uint32_t mode_setting=0;
    bool local_player=false, bypass=false;
    double throttle=.5, engagement=.5, clutch_gain=0, angular_speed=300,
           coupling_resistance=0, effective_torque=100, transmitted_torque=0,
           reference_rotation=0, output_torque=0, driven_speed=0,
           previous_rotation=0, drag_speed=0, prior_output_rotation=0,
           final_drive_acceleration=0, gearbox_drag=0, output_rotation=0,
           wheel_acceleration=0, accumulated_drag=0, inertia_sum=1,
           longitudinal_speed=0, acceleration=0, speed=0, alternate_speed=0,
           damage_one=0, damage_two=0, request=0;
};
struct DriveConfig {
    std::vector<double> gear_ratios, gear_losses, inertia_factors, speed_factors;
    double final_drive=0, torque_capacity=0, efficiency=0;
    std::int32_t clutch_steps=0, maximum_rpm=0;
    bool third_enabled=false;
    double option_one=0, option_two=0;
    std::int32_t option_kind=0;
    double increment_gain=0, secondary_gain=0;
    std::int32_t secondary_kind=0;
};
struct DriveCall {
    std::string stage;
    std::optional<std::int32_t> code;
    std::vector<double> values;
    bool operator==(const DriveCall&) const=default;
};
// Required damage/component consumers and per-wheel service observations.
// A vehicle_gate call must return a boolean; effects may return nullopt.
using DriveExecutor=std::function<std::optional<bool>(const DriveCall&,DriveState&)>;
std::uint32_t vehicle_control_mode(std::uint32_t flags, bool is_local_vehicle,
                                   std::uint32_t setting);
DriveState update_clutch(DriveState,DriveConfig);
DriveState prepare_drive(DriveState,DriveConfig);
DriveState accumulate_drive_request(DriveState,DriveConfig);
DriveState distribute_drive(DriveState,DriveConfig,const DriveExecutor&);
DriveState apply_drive_forces(DriveState,DriveConfig,const DriveExecutor&);
}
