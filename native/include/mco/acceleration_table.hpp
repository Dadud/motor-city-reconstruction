#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
namespace mco {
// Original 0x538660; secondary is an observed but unused sixth ABI argument.
double startup_force(std::span<const std::byte> configuration,std::span<const std::byte> record,
    std::int32_t rpm,unsigned selector,float sample,bool secondary=false);
// Original 0x5384f0; preserves every byte outside 0x128..0x4a7 outputs.
std::array<std::byte,0x4a8> acceleration_table(std::span<const std::byte> configuration,
    std::span<const std::byte> record);
}
