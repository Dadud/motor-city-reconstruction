#pragma once
#include <array>
#include <cstdint>

namespace mco {
struct BrakeThermalAxle {
    double temperature, diameter, cooling_coefficient, heat_capacity_factor;
    double thermal_mass, temperature_limit;
    std::uint32_t material_code, construction_code;
    std::int32_t countdown;
};
struct BrakeWorkWheel {double brake_force,spin_scale,spin_value;};
struct BrakeThermalState {
    BrakeThermalAxle front,rear;
    std::array<BrakeWorkWheel,4> wheels;
    double service_control;
    bool parking_control;
    double speed,mass_parameter,elevation_parameter;
    bool environment_flag;
    std::int32_t environment_code;
    double kinetic_value=0,elevation_value=0;
};
std::int32_t brake_countdown(double diameter,std::uint32_t material,std::uint32_t construction);
double brake_fade(double temperature,double limit);
double brake_ambient(bool flag,std::int32_t code);
BrakeThermalState update_brake_thermal(BrakeThermalState state);
}
