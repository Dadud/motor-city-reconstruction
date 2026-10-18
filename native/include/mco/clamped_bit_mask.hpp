#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
namespace mco {
// Original 0x403370; Increment with 32-bit wrap, clamp to 0..15 and choose the reversed bit.
std::uint32_t clamped_bit_mask(std::int32_t index);
}
