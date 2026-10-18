#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
namespace mco {
// Original 0x42d380; Read one byte from a flat table, with a -1 index sentinel.
std::uint8_t table_byte_read(std::span<const std::byte> table, std::int32_t index);
}
