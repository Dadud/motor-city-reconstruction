#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
#include "mco/input_key_queue.hpp"
namespace mco {
// Original 0x584450; Produce raw key state and repeated queue records with original synchronization ordering.
std::uint32_t input_key_down(InputKeyQueue &state, std::span<const std::byte, 128> remap, std::uint32_t enabled, std::uint32_t window, std::uint32_t message, std::uint32_t key, std::uint32_t message_bits);
}
