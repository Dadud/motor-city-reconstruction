#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
namespace mco {
// Original 0x423310; Predicate stored back: one when the value is zero.
std::uint32_t zero_flag(std::uint32_t value);
}
