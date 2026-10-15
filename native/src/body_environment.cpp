#include "mco/body_environment.hpp"
#include "mco/air_density.hpp"
#include <utility>

namespace mco {
BodyEnvironmentOutput calculate_body_environment(BodyResistanceState body,const BodyEnvironment& environment) {
    const double density=calculate_air_density(environment.altitude,environment.cold_environment,
        environment.weather_enabled,environment.weather_code);
    const auto wind=calculate_wind(environment.wind);
    auto drafting=calculate_drafting(environment.current_vehicle,environment.vehicles);
    body.density=density;
    body.wind_lateral=wind.body_velocity[0];
    body.wind_longitudinal=wind.body_velocity[2];
    body.drafting_factor=drafting.factor;
    return {calculate_body_resistance(body),density,wind,std::move(drafting)};
}
}
