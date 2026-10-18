#pragma once
#include "mco/input_mouse_press.hpp"
#include "mco/input_mouse_motion.hpp"
namespace mco {
inline std::uint32_t window_mouse_binding(MouseInputState& mouse,const MousePlatformBridge& platform,
    std::uint32_t handler,std::uint32_t owner,std::uint32_t window,std::uint32_t message,
    std::uint32_t wparam,std::uint32_t lparam) {
    if(handler==0x584670) return input_mouse_press(mouse,platform,owner,window,message,wparam,lparam);
    if(handler==0x5846d0) return input_mouse_motion(mouse,platform,owner,window,message,wparam,lparam);
    throw std::invalid_argument("window handler has no recovered mouse binding");
}
}
