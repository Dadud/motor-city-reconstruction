#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
namespace mco {
// Original 0x42d350; Read one byte from a 300-column table, with a -1 column sentinel.
std::uint8_t table_byte_read_xy(std::span<const std::byte> table, std::int32_t row, std::int32_t column);
}
