#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
namespace mco {
// Original 0x4030e0; Read the selected entity flag with a null-table default.
std::uint32_t entity_side_flag(std::span<const std::byte> table, std::uint32_t index, std::uint32_t side);
}
