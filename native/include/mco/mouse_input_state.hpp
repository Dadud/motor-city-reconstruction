#pragma once
#include "mco/window_dispatch_state.hpp"
namespace mco {
using MouseClientToScreen=std::uint32_t (*)(std::uint32_t window,std::uint32_t& x,std::uint32_t& y,void* user);
using MouseSetPosition=void (*)(std::uint32_t x,std::uint32_t y,void* user);
using MouseSetCursor=void (*)(std::uint32_t identity,void* user);
using MouseButtonNotify=void (*)(std::uint32_t identity,std::uint32_t buttons,void* user);
struct MousePlatformBridge {
    MouseClientToScreen client_to_screen{};
    MouseSetPosition set_position{};
    MouseSetCursor set_cursor{};
    MouseButtonNotify notify_buttons{};
    void* user{};
};
struct MouseInputState {
    WindowDispatchState& window;
    std::span<std::byte,mouse_input_image::size> image;
    std::uint32_t enabled,button_callback;
    std::uint32_t load(std::size_t offset) const {return detail::read_word(image,offset);}
    void store(std::size_t offset,std::uint32_t value) {detail::write_word(image,offset,value);}
};
}
