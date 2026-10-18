#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
namespace mco {
// Original 0x428980; Predicate: the value equals the sentinel constant 0xfeeeeb19.
std::uint32_t sentinel_match(std::uint32_t value);
}
