#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
#include "mco/mouse_input_state.hpp"
namespace mco {
// Original 0x584670; Preserve original mouse/cursor state transitions with explicit platform bridges.
std::uint32_t input_mouse_press(MouseInputState &mouse, const MousePlatformBridge &platform, std::uint32_t enabled, std::uint32_t window, std::uint32_t message, std::uint32_t wparam, std::uint32_t lparam);
}
