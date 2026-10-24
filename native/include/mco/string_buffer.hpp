#pragma once
#include <cstddef>
#include <cstdint>
#include <span>

namespace mco {
// Original 0x415410, unique inline-buffer in-place branch only.
std::uint32_t assign_inline_buffer(std::span<std::byte> destination,
                                  std::span<const std::byte> source,
                                  std::uint32_t length,
                                  std::uint32_t capacity);
}
