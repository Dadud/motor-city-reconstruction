#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
namespace mco {
// Original 0x435fb0; Find an identifier through the current 256-byte record, always checking the base.
std::uint32_t record_stack_contains(std::span<const std::byte> records, std::uint32_t base, std::uint32_t cursor, std::uint32_t identifier);
}
