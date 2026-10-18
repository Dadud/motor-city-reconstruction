#pragma once
#include "mco/input_mouse_update.hpp"
namespace mco::detail {
inline std::uint32_t input_mouse_message(MouseInputState& mouse,const MousePlatformBridge& platform,
    std::uint32_t enabled,std::uint32_t window,std::uint32_t wparam,std::uint32_t lparam,std::uint32_t notify) {
    if(enabled!=0 && window==mouse.window.load(input_queue_image::target_window)) {
        const auto buttons=(wparam&1u)|((wparam&2u) ? 2u:0u)|((wparam&16u) ? 4u:0u);
        input_mouse_update(mouse,platform,lparam&65535u,lparam>>16,buttons,notify);
    }
    return 0;
}
}
