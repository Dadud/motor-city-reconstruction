#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
namespace mco {
// Original 0x4077a0; Write three dwords into a registry slot.
void registry_slot_write(std::span<std::byte> registry, std::uint32_t slot, std::uint32_t first, std::uint32_t second, std::uint32_t third);
}
