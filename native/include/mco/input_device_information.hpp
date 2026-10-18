#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
#include "mco/input_device_information_bridge.hpp"
namespace mco {
// Original 0x6f0b20; Build device information and bounded button/axis/POV probe masks from virtual records.
std::uint32_t input_device_information(InputDeviceBridge &device, const InputDeviceInformationBridge &platform, std::span<std::byte,540> output);
}
