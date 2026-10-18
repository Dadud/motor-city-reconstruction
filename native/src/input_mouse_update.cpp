#include "mco/input_mouse_update.hpp"
#include <stdexcept>
#include <bit>
#include "mco/input_cursor_warp.hpp"

namespace mco {

// Decompiled pseudocode of 0x6f08d0, kept as the implementation draft.
// The oracle against the original, not this text, decides correctness.


void input_mouse_update(MouseInputState &mouse, const MousePlatformBridge &platform, std::uint32_t x, std::uint32_t y, std::uint32_t buttons, std::uint32_t notify) {
    using namespace mouse_input_image;
    if(mouse.enabled==0) return;
    const auto synchronizer=mouse.window.load(input_queue_image::dispatch_synchronizer);
    if(synchronizer==0) return;
    auto clamp=[](std::uint32_t value,std::uint32_t lower,std::uint32_t upper) {
        const auto v=std::bit_cast<std::int32_t>(value),lo=std::bit_cast<std::int32_t>(lower),hi=std::bit_cast<std::int32_t>(upper);
        const auto at_least=v>lo ? v:lo;
        return std::bit_cast<std::uint32_t>(at_least<hi ? (v>lo ? v:lo):hi);
    };
    const auto target_x=clamp(x,mouse.load(minimum_x),mouse.load(maximum_x));
    const auto target_y=clamp(y,mouse.load(minimum_y),mouse.load(maximum_y));
    if(!mouse.window.sync) throw std::invalid_argument("mouse synchronization bridge required");
    mouse.window.sync(mouse.window,true,synchronizer,mouse.window.user);
    mouse.store(mouse_input_image::buttons,buttons);
    if(target_x!=x || target_y!=y) input_cursor_warp(mouse.window,platform,target_x,target_y);
    if(target_x!=mouse.load(mouse_input_image::x) || target_y!=mouse.load(mouse_input_image::y)) {
        mouse.store(mouse_input_image::x,target_x);mouse.store(mouse_input_image::y,target_y);
    }
    mouse.window.synchronize(false);
    if(notify!=0 && mouse.button_callback!=0) {
        if(!platform.notify_buttons) throw std::invalid_argument("mouse button notification bridge required");
        platform.notify_buttons(mouse.button_callback,buttons,platform.user);
    }
}

}  // namespace mco
