#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
#include "mco/window_dispatch_state.hpp"
namespace mco {
// Original 0x582e40; Insert, replace or remove a message handler with original search/sort and synchronization behavior.
std::uint32_t window_handler_register(WindowDispatchState &state, std::uint32_t message, std::uint32_t handler);
}
