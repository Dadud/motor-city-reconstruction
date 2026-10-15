#pragma once
#include <cstddef>
#include <span>
#include <cstdint>
namespace mco {
// Original startup producers. Physical coefficient units remain unresolved.
float startup_load_coefficient(std::span<const std::byte> configuration);
float startup_balance_coefficient(std::span<const std::byte> configuration,bool alternate_load=false);
float brake_diameter(std::uint32_t code);
double brake_capacity(float diameter,std::uint32_t material,std::uint32_t construction,float pressure,bool auxiliary);
float startup_brake_balance(std::span<const std::byte> configuration);
}
