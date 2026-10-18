#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
#include "mco/window_procedure_bridge.hpp"
namespace mco {
// Original 0x583290; Return the handled local result or invoke the original default window-procedure bridge.
std::uint32_t window_procedure(WindowDispatchState &state, const WindowProcedureBridge &bridge, std::uint32_t window, std::uint32_t message, std::uint32_t wparam, std::uint32_t lparam);
}
