#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
namespace mco {
// Original 0x414bf0; OR a mask into the 0x6c state word.
std::uint32_t state_or_mask(std::uint32_t state, std::uint32_t mask);
}
