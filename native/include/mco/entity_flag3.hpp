#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
namespace mco {
// Original 0x403440; Wave-0 entity predicate: bit 3 of the record flag byte, inverted.
std::uint32_t entity_flag3(std::span<const std::byte> table, std::uint32_t index);
}
