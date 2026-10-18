#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
namespace mco {
// Original 0x43ad80; Copy two bytes with the second staged first, then append a zero.
void copy_prefix2(std::span<std::byte,3> destination, std::span<const std::byte,2> source);
}
