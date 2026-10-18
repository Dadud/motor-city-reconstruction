#pragma once
#include "mco/input_key_down.hpp"
#include "mco/input_key_release.hpp"
#include "mco/input_character.hpp"
namespace mco {
// Bind recovered keyboard callback identities to native implementations.
// Other registrations require their own implementations; never silently handle them.
inline std::uint32_t window_keyboard_binding(InputKeyQueue& queue,std::span<const std::byte,128> remap,
    std::uint32_t handler,std::uint32_t owner,std::uint32_t window,std::uint32_t message,
    std::uint32_t wparam,std::uint32_t lparam) {
    if(handler==0x584450) return input_key_down(queue,remap,owner,window,message,wparam,lparam);
    if(handler==0x584610) return input_key_release(queue.keys,remap,queue.load(input_queue_image::remap),
        owner,window,queue.load(input_queue_image::target_window),lparam);
    if(handler==0x584370) return input_character(queue,owner,window,message,wparam,lparam);
    throw std::invalid_argument("window handler has no recovered keyboard binding");
}
}
