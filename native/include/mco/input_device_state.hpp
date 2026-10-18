#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
#include "mco/input_device_access.hpp"
namespace mco {
// Original 0x6f03c0; Select device information or keyboard state, running actual poll/read wrappers for keyboard acquisition.
std::span<const std::byte> input_device_state(InputDeviceAccess &access, std::uint32_t kind);
}
