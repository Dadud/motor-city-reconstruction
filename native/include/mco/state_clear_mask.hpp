#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
namespace mco {
// Original 0x414c30; Member: clear the masked bits of the state.
std::uint32_t state_clear_mask(std::uint32_t state, std::uint32_t mask);
}
