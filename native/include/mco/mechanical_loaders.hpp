#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
namespace mco {
struct ComponentLoadResult {
    std::uint32_t status;
    std::array<std::byte,0x820> configuration;
    std::array<std::byte,0x984> component;
};
// Internal image adapter for recovered loaders; unsupported kinds fail explicitly.
ComponentLoadResult load_mechanical_component(std::uint32_t abstract_type,
    std::span<const std::byte> configuration,std::span<const std::byte> component);
}
