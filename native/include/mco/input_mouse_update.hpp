#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
#include "mco/mouse_input_state.hpp"
namespace mco {
// Original 0x6f08d0; Preserve original mouse/cursor state transitions with explicit platform bridges.
void input_mouse_update(MouseInputState &mouse, const MousePlatformBridge &platform, std::uint32_t x, std::uint32_t y, std::uint32_t buttons, std::uint32_t notify);
}
