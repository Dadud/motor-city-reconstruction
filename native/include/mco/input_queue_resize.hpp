#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
#include "mco/input_key_queue.hpp"
namespace mco {
// Original 0x584ca0; Clamp queue capacity to one through thirty-two and reset both cursors.
void input_queue_resize(InputKeyQueue &state, std::uint32_t requested);
}
