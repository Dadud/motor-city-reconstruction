#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
#include "mco/window_dispatch_state.hpp"
namespace mco {
// Original 0x583210; Dispatch a registered window message with original synchronization and callback argument order.
std::uint32_t window_message_dispatch(WindowDispatchState &state, std::uint32_t window, std::uint32_t message, std::uint32_t wparam, std::uint32_t lparam, std::uint32_t result_identity);
}
