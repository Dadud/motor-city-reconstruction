#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
namespace mco {
// Original 0x4325c0; Normalize six signed selection words and return the fourth division quotient.
std::uint32_t selection_state_normalize(std::span<std::byte, 24> state);
}
