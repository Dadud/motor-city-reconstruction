#pragma once
#include "mco/input_device_bridge.hpp"
namespace mco {
// record is an original-sized temporary view. Only its size tag is defined
// before its first call. Populate all fields that the routine will read.
using InputDeviceInformationInvoke=std::uint32_t (*)(InputDeviceBridge&,std::uint32_t table,std::uint32_t method,std::span<std::byte> record,std::uint32_t selector,std::uint32_t flags,void* user);
struct InputDeviceInformationBridge {
    std::span<const std::uint32_t,8> axis_offsets;
    InputDeviceInformationInvoke invoke{};
    void* user{};
};
}
