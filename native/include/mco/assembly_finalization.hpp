#pragma once
#include <array>
#include <cstddef>
#include <span>
namespace mco {
// Internal mechanical configuration adapter, not a mod API or assembly proof.
std::array<std::byte,0x820> finalize_loaded_configuration(
    std::span<const std::byte> configuration,bool components_loaded);
}
