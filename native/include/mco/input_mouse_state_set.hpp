#pragma once
#include "mco/input_mouse_lifetime_state.hpp"
namespace mco {
// References to existing observations; these do not own or copy game globals.
struct InputMouseStateSet {
    InputMouseLifetimeState& lifetime;
    std::uint32_t& access_mode;
    std::uint32_t& state8;
    std::uint32_t& state9;
    std::uint32_t& diagnostic_callback;
    std::uint32_t& diagnostic_file;
    std::uint32_t& diagnostic_line;
};
// resolve returns an opaque token for the current virtual table. invoke looks
// up code's slot in that captured table at invocation time, independently of
// the separately reloaded this identity. Direct helper calls use table zero.
struct InputMouseStateSetPlatform {
    std::uint32_t (*resolve)(InputMouseStateSet&,std::uint32_t identity,void*){};
    std::uint32_t (*invoke)(InputMouseStateSet&,std::uint32_t code,
        std::uint32_t target,std::uint32_t identity,
        std::span<const std::uint32_t> arguments,void*){};
    void* user{};
};
bool input_mouse_state_set(InputMouseStateSet&,const InputMouseStateSetPlatform&,
                           std::uint32_t selector,std::uint32_t value);
}
