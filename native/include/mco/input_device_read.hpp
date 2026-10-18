#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
#include "mco/input_device_bridge.hpp"
namespace mco {
// Original 0x6f0a30, 0x6f0a70, 0x6f0aa0; Poll and read device state with one acquisition retry and zero-fill on final read failure.
std::uint32_t input_device_read(InputDeviceBridge &device, std::span<std::byte> destination, std::uint32_t size);
}
