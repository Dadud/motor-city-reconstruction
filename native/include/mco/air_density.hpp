#pragma once
#include <cstdint>
namespace mco {
double calculate_air_density(double altitude,bool cold_environment,bool weather_enabled,std::uint32_t weather_code);
}
