#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
namespace mco {
// Original 0x4081c0; Member 12-byte copy.
void buffer_copy12_a(std::span<std::byte,12> destination, std::span<const std::byte,12> source);
}
