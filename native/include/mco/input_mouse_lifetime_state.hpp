#pragma once
#include <array>
#include <cstdint>
#include <span>
namespace mco {
// Fifteen observed words at 0xb361fc..0xb36234, not an original class layout.
struct InputMouseLifetimeState {
    std::array<std::uint32_t,15>& words;
    std::uint32_t& width;
    std::uint32_t& height;
};
namespace mouse_lifetime_call {
inline constexpr std::uint32_t module=0x100,create=0x101,cursor=0x102,client=0x103;
inline constexpr std::uint32_t query=0,release=8,create_device=0xc,property=0x18,unacquire=0x20,format=0x2c;
}
// Opaque identities resolve through the bridge's current virtual table. Output
// slots: 1 interface, 2 local temporary, 3 device, 4 two-word POINT.
using InputMouseLifetimeInvoke=std::uint32_t (*)(InputMouseLifetimeState&,std::uint32_t code,
    std::uint32_t identity,std::span<const std::uint32_t> arguments,std::uint32_t output_slot,
    std::span<std::uint32_t> output,void* user);
struct InputMouseLifetimePlatform {InputMouseLifetimeInvoke invoke{};void* user{};};
void input_mouse_cleanup(InputMouseLifetimeState&,const InputMouseLifetimePlatform&);
}
