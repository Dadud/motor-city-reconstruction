#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
#include "mco/input_device_lifetime_state.hpp"
namespace mco {
// Original 0x6f0200, 0x6f0310, 0x6f0350, 0x6f0360, 0x584cf0; Initialize device interfaces, preserve failure cleanup and registration behavior, and expose set-state/window access.
std::uint32_t input_device_initialize(InputDeviceLifetimeState &state, const InputDeviceLifetimePlatform &platform, std::uint32_t incoming_temporary);
}
