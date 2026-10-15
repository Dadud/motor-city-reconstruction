#pragma once
#include "mco/body_resistance.hpp"
#include "mco/drafting.hpp"
#include "mco/wind.hpp"
#include <cstdint>

namespace mco {
struct BodyEnvironment {
    double altitude;
    bool cold_environment,weather_enabled;
    std::uint32_t weather_code;
    WindState wind;
    std::int64_t current_vehicle;
    std::vector<DraftVehicle> vehicles;
};
struct BodyEnvironmentOutput {
    BodyResistanceOutput body;
    double density;
    WindOutput wind;
    DraftingOutput drafting;
};
// Retain returned peer geometry and wheel loads when advancing simulation state.
BodyEnvironmentOutput calculate_body_environment(BodyResistanceState body,const BodyEnvironment& environment);
}
