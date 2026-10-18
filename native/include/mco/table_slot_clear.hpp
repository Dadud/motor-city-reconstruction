#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
namespace mco {
// Original 0x424cc0; Clear the second word of a nonnull table target.
void table_slot_clear(std::span<const std::span<std::byte>> table, std::uint32_t slot);
}
