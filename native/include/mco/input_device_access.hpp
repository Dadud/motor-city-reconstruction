#pragma once
#include "mco/input_device_bridge.hpp"
#include "mco/layouts.hpp"
namespace mco {
// These images retain the four-byte prefix before the 256 keyboard bytes.
struct InputDeviceAccess;
using InputDeviceResolve=InputDeviceBridge& (*)(std::uint32_t identity,void* user);
using InputDeviceInformation=std::uint32_t (*)(InputDeviceAccess&,std::uint32_t identity,std::span<std::byte> output,void* user);
using InputInvalidKind=void (*)(InputDeviceAccess&,std::uint32_t kind,void* user);
struct InputDeviceAccess {
    // References alias the original shared globals across lifecycle views.
    std::uint32_t &enabled,&device;
    std::span<std::byte,direct_key_image::size> keyboard;
    std::span<std::byte,input_device_information_image::size> information;
    std::uint32_t &diagnostic_file,&diagnostic_line;
    InputDeviceResolve resolve{};
    InputDeviceInformation get_information{};
    InputInvalidKind invalid_kind{};
    void* user{};
};
}
