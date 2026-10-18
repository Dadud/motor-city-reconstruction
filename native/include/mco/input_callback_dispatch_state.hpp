#pragma once
#include "mco/input_device_callback.hpp"
namespace mco {
struct InputCallbackDispatchState {InputDeviceCallback& callback;std::uint32_t& enabled;};
using InputCallbackAvailability=std::uint32_t (*)(InputCallbackDispatchState&,void* user);
using InputCallbackRead=std::uint32_t (*)(InputCallbackDispatchState&,void* user);
using InputCallbackInvoke=std::uint32_t (*)(InputCallbackDispatchState&,std::uint32_t identity,void* user);
struct InputCallbackDispatchPlatform {
    InputCallbackAvailability available{};
    InputCallbackRead read{};
    InputCallbackInvoke invoke{};
    void* user{};
};
// Original 0x6f01d0 explicitly zero-extends its selected byte into EAX.
std::uint32_t input_callback_fallback(InputCallbackDispatchState&,const InputCallbackDispatchPlatform&);
}
