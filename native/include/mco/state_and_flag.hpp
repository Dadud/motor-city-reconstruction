#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
namespace mco {
// Original 0x414c10; Member predicate: nonzero when state and mask share bits.
std::uint32_t state_and_flag(std::uint32_t state, std::uint32_t mask);
}
