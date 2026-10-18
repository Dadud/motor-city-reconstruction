#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
namespace mco {
// Original 0x423420; Indexed dword read from the first lookup table.
std::uint32_t table_read_a(std::span<const std::byte> table, std::uint32_t index);
}
