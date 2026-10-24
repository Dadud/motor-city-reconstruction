#pragma once
#include "mco/window_dispatch_state.hpp"
#include <array>
#include <cstddef>
#include <cstdint>
#include <span>

namespace mco {
struct WindowFocusState;
using FocusDefaultProcedure=std::uint32_t (*)(WindowFocusState&,std::uint32_t window,
    std::uint32_t message,std::uint32_t wparam,std::uint32_t lparam,void* user);
using FocusUnhook=std::uint32_t (*)(WindowFocusState&,std::uint32_t hook,void* user);
using FocusGetModule=std::uint32_t (*)(WindowFocusState&,void* user);
using FocusSetHook=std::uint32_t (*)(WindowFocusState&,std::uint32_t id,
    std::uint32_t callback,std::uint32_t module,std::uint32_t thread,void* user);

struct WindowFocusState {
    WindowDispatchState& dispatch;
    std::span<std::byte,4> active_flag;  // DAT_00acae2c; separate from the 0x530-byte queue image
    std::span<std::byte,128> raw_keys;  // DAT_008c8648
    FocusDefaultProcedure default_procedure{};
    FocusUnhook unhook{};
    FocusGetModule get_module{};
    FocusSetHook set_hook{};
    void* user{};
    std::uint32_t keyboard_hook() const {return dispatch.load(input_queue_image::keyboard_hook);}
    void set_keyboard_hook(std::uint32_t value) {dispatch.store(input_queue_image::keyboard_hook,value);}
    std::uint32_t mouse_hook() const {return dispatch.load(input_queue_image::mouse_hook);}
    void set_mouse_hook(std::uint32_t value) {dispatch.store(input_queue_image::mouse_hook,value);}
    std::uint32_t active() const {return detail::read_word(active_flag,0);}
    void set_active(std::uint32_t value) {detail::write_word(active_flag,0,value);}
};
}
