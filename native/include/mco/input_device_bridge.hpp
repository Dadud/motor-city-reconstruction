#pragma once
#include <cstdint>
#include <cstddef>
#include <span>
namespace mco {
struct InputDeviceBridge;
// The original reloads the object's vtable before each virtual call. Table
// identities are opaque; the bridge may replace table during any method.
using InputDeviceInvoke=std::uint32_t (*)(InputDeviceBridge&,std::uint32_t table,std::uint32_t method,std::span<std::byte> destination,std::uint32_t size,void* user);
struct InputDeviceBridge {
    std::uint32_t identity,table;
    InputDeviceInvoke invoke{};
    void* user{};
};
// Original 0x6f0a70 and 0x6f0aa0. Status is the final EAX value.
std::uint32_t input_device_poll(InputDeviceBridge& device);
std::uint32_t input_device_read_retry(InputDeviceBridge& device,std::span<std::byte> destination,std::uint32_t size);
}
