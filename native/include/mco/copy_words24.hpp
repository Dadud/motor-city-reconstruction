#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
namespace mco {
// Original 0x43f960; Copy six words in the original read/write order, including overlapping spans.
std::span<std::byte,24> copy_words24(std::span<std::byte,24> destination, std::span<const std::byte,24> source);
}
