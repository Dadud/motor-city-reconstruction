#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
#include "mco/window_dispatch_state.hpp"
namespace mco {
// Original 0x583c30; Initialize the input queue and install the original 28 message registrations once.
std::uint32_t window_input_initialize(WindowDispatchState &state);
}
