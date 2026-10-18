#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
namespace mco {
// Original 0x4acdc0; Query raw key level or a latched press while updating latch bits.
std::uint32_t input_key_query(std::span<const std::byte, 128> keys, std::span<std::byte> latches, std::uint32_t code, std::uint32_t press_only);
}
