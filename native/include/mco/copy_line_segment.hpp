#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
namespace mco {
// Original 0x433e70; Copy through an inclusive byte limit or newline and return the skipped source offset.
std::uint32_t copy_line_segment(std::span<std::byte> destination, std::span<const std::byte> source, std::int32_t inclusive_limit);
}
