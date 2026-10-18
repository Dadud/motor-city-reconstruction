#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
#include "mco/input_key_queue.hpp"
namespace mco {
// Original 0x584370; Queue repeated character messages with original event-store, cursor and synchronization ordering.
std::uint32_t input_character(InputKeyQueue &state, std::uint32_t enabled, std::uint32_t window, std::uint32_t message, std::uint32_t character, std::uint32_t message_bits);
}
