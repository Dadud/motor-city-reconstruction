#pragma once
#include <array>
#include <cstdint>
#include <span>
namespace mco {
struct GearBinding {
    std::array<double,8> rpm_per_speed{},speed_per_rpm{},loss_final_ratio{},
        wheel_inertia_factors{},inverse_near_limit_speed{};
    double final_drive_inertia=0;
};
// Requires finalized component observations; does not assemble a vehicle.
GearBinding bind_gear_tables(std::int32_t maximum_rpm,double rear_width,
    double rear_aspect,double rear_rim,std::span<const double> gear_ratios,
    std::span<const double> gear_losses,double final_drive);
}
