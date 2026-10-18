#pragma once
#include "mco/input_key_queue.hpp"
#include "mco/input_device_callback.hpp"
namespace mco {
struct InputDeviceLifetimeState {
    InputKeyQueue& queue;
    std::uint32_t &interface_handle,&device;
    std::uint32_t initialized,cleanup_registered;
    InputDeviceCallback callback;
    std::uint32_t &diagnostic_file,&diagnostic_line;
};
namespace device_lifetime_call {
inline constexpr std::uint32_t create_sync=0x100,module_handle=0x101,create_input=0x102,register_cleanup=0x103,diagnostic=0x104;
inline constexpr std::uint32_t query=0,release=8,create_device=0xc,unacquire=0x20,set_format=0x2c,set_cooperative=0x34;
}
// Virtual calls resolve the supplied opaque handle's current table. Output
// slots identify interface (1), temporary (2), or device (3); no host pointer
// is encoded as an original address. Temporary slots live through initialize.
using InputDeviceLifetimeInvoke=std::uint32_t (*)(InputDeviceLifetimeState&,std::uint32_t code,std::uint32_t identity,std::span<const std::uint32_t> arguments,std::uint32_t output_slot,std::uint32_t* output,void* user);
struct InputDeviceLifetimePlatform {InputDeviceLifetimeInvoke invoke{};void* user{};};
void input_device_cleanup(InputDeviceLifetimeState&,const InputDeviceLifetimePlatform&);
void input_device_shutdown(InputDeviceLifetimeState&,const InputDeviceLifetimePlatform&);
std::uint32_t input_device_set_state(InputDeviceLifetimeState&,const InputDeviceLifetimePlatform&,std::uint32_t kind,std::uint32_t value);
std::uint32_t input_device_window(InputKeyQueue&);
}
