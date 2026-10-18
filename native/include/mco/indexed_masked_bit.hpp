#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
namespace mco {
// Original 0x403320; Read a record mask and apply the clamped reversed bit.
std::uint32_t indexed_masked_bit(std::span<const std::byte> records, std::uint32_t record, std::int32_t index);
}
