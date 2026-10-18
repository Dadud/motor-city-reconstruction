#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
namespace mco {
// Original 0x489cb0; Test the camera context kind and secondary mode.
std::uint32_t camera_context_special(std::span<const std::byte, 12> context);
}
