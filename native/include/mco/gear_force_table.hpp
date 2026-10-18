#pragma once
#include <array>
#include <cstddef>
#include <span>
namespace mco {
// Complete 0x53b260, with recovered 0x548f00 torque interpolation.
// Configuration is an assembled 0x820-byte little-endian record.
std::array<float,135> gear_force_table(std::span<const std::byte> configuration,
    const std::array<float,8>& rpm_steps, unsigned selector);
}
