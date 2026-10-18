#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
namespace mco {
// Original 0x42f070; Indexed dword read from the second lookup table.
std::uint32_t table_read_b(std::span<const std::byte> table, std::uint32_t index);
}
