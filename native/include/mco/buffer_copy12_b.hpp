#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
namespace mco {
// Original 0x408510; Member 12-byte copy, byte-identical twin of 0x4081c0.
void buffer_copy12_b(std::span<std::byte,12> destination, std::span<const std::byte,12> source);
}
