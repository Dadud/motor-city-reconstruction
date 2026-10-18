#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
#include "mco/input_default_key_state.hpp"
namespace mco {
// Original 0x6f0580, 0x6f0e80; Read the default queue callback and route its low word through overlapping action maps and handler words.
std::uint32_t input_default_key(InputDefaultKeyState &state, const InputCallbackDispatchPlatform &platform);
}
