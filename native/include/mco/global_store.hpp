#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
namespace mco {
// Original 0x406a30; Wave-0 global store-and-return leaf.
std::uint32_t global_store(std::array<std::byte,4>& destination, std::uint32_t stored_value, std::uint32_t returned_value);
}
