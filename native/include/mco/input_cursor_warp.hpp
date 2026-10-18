#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
#include "mco/mouse_input_state.hpp"
namespace mco {
// Original 0x582fe0; Preserve original mouse/cursor state transitions with explicit platform bridges.
void input_cursor_warp(WindowDispatchState &window, const MousePlatformBridge &platform, std::uint32_t x, std::uint32_t y);
}
