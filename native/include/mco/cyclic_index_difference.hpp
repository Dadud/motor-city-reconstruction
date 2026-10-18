#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
namespace mco {
// Original 0x403220; Compute the original wrapped index difference and optional half-ring adjustment.
std::int32_t cyclic_index_difference(std::int32_t first, std::int32_t second, std::int32_t count, std::uint32_t mode);
}
