#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
namespace mco {
// Original 0x433dd0; Match either orientation of a pair, stopping at the first-word sentinel.
std::uint32_t record_pair_match(std::span<const std::byte> pairs, std::uint32_t first, std::uint32_t second);
}
