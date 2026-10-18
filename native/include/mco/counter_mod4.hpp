#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
namespace mco {
// Original 0x42cc60; Advance a counter modulo four.
std::uint32_t counter_mod4(std::uint32_t counter);
}
