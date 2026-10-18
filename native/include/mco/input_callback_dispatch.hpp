#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
#include "mco/input_callback_dispatch_state.hpp"
namespace mco {
// Original 0x6f0450, 0x6f01d0; Return the selected callback result or the conditionally read, byte-masked fallback value.
std::uint32_t input_callback_dispatch(InputCallbackDispatchState &state, const InputCallbackDispatchPlatform &platform);
}
