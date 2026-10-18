#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
namespace mco {
// Original 0x460670; Read the raw aliased key byte after a signed range check.
std::uint32_t input_key_raw(std::span<const std::byte, 128> keys, std::uint32_t code);
}
