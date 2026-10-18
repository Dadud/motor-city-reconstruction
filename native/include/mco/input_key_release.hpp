#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
namespace mco {
// Original 0x584610; Apply a matching-window key-release message and optional scan remapping.
std::uint32_t input_key_release(std::span<std::byte> keys, std::span<const std::byte, 128> remap, std::uint32_t remap_present, std::uint32_t enabled, std::uint32_t message_window, std::uint32_t target_window, std::uint32_t message_bits);
}
