#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
namespace mco {
// Original 0x4072c0; Wave-0 registry: assign a node the next id and link it at the head.
std::uint32_t registry_register(std::span<std::byte,0x58> node, std::uint32_t counter, std::uint32_t head);
}
