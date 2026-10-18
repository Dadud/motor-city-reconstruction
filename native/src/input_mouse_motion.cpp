#include "mco/input_mouse_motion.hpp"
#include <stdexcept>
#include "mco/detail/input_mouse_message.hpp"

namespace mco {

// Decompiled pseudocode of 0x5846d0, kept as the implementation draft.
// The oracle against the original, not this text, decides correctness.


std::uint32_t input_mouse_motion(MouseInputState &mouse, const MousePlatformBridge &platform, std::uint32_t enabled, std::uint32_t window, std::uint32_t message, std::uint32_t wparam, std::uint32_t lparam) {
    (void)message;
    return detail::input_mouse_message(mouse,platform,enabled,window,wparam,lparam,0);
}

}  // namespace mco
