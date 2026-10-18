#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
#include "mco/input_keyboard_layout_state.hpp"
namespace mco {
// Original 0x6f09f0; Select the original keyboard scan remap using cached platform keyboard-type queries.
std::uint32_t input_keyboard_layout(InputKeyQueue &queue, const InputKeyboardLayoutPlatform &platform);
}
