#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
namespace mco {
// Original 0x407d70; Predicate: a registry slot holds a nonzero first field.
std::uint32_t registry_slot_used(std::span<const std::byte> registry, std::uint32_t slot);
}
