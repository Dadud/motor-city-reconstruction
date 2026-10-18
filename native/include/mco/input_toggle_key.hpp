#pragma once
#include "mco/input_toggle_key_platform.hpp"
namespace mco {
// Original 0x6bfc90; selector 0/1/2 chooses Caps/Num/Scroll Lock.
void input_toggle_key(std::uint32_t selector, std::uint32_t desired,
                      const InputToggleKeyPlatform& platform);
// Original 0x6bfc80.
void input_startup_numlock(const InputToggleKeyPlatform& platform);
}
