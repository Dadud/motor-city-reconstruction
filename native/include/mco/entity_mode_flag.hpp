#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
namespace mco {
// Original 0x403470; Read the selected entity flag with a null-table default.
std::uint32_t entity_mode_flag(std::span<const std::byte> table, std::uint32_t index, std::uint8_t side);
}
