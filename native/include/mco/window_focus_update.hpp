#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
#include "mco/window_focus_state.hpp"
namespace mco {
// Original 0x584070; Handle WM_ACTIVATE key-state clearing and global keyboard/mouse hook lifecycle.
std::uint32_t window_focus_update(WindowFocusState &state, std::uint32_t window, std::uint32_t message, std::uint32_t wparam, std::uint32_t lparam, std::uint32_t &result);
}
