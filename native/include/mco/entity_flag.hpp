#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
namespace mco {
// Original 0x405df0; Wave-0 entity flag predicate over 28-byte records.
std::uint32_t entity_flag(std::span<const std::byte> table, std::uint32_t index);
}
