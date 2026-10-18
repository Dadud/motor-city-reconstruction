#include "mco/input_cursor_warp.hpp"
#include <stdexcept>

namespace mco {

// Decompiled pseudocode of 0x582fe0, kept as the implementation draft.
// The oracle against the original, not this text, decides correctness.


void input_cursor_warp(WindowDispatchState &window, const MousePlatformBridge &platform, std::uint32_t x, std::uint32_t y) {
    if(!platform.client_to_screen || !platform.set_position || !platform.set_cursor)
        throw std::invalid_argument("cursor platform bridge required");
    auto screen_x=x,screen_y=y;
    const auto converted=platform.client_to_screen(window.load(input_queue_image::target_window),screen_x,screen_y,platform.user);
    if(converted) platform.set_position(screen_x,screen_y,platform.user);
    else platform.set_position(x,y,platform.user);
    platform.set_cursor(0,platform.user);
}

}  // namespace mco
