#include "mco/window_focus_update.hpp"
#include <algorithm>
#include <stdexcept>

namespace mco {
std::uint32_t window_focus_update(WindowFocusState& state,std::uint32_t window,
    std::uint32_t message,std::uint32_t wparam,std::uint32_t lparam,
    std::uint32_t& result) {
    auto& dispatch=state.dispatch;
    if(dispatch.enabled==0 || window!=dispatch.load(input_queue_image::target_window))
        return 1;

    const bool inactive=(wparam&0xffffu)==0 || (wparam>>16)!=0;
    if(inactive) {
        if(state.active()!=0) state.set_active(0);
        if(dispatch.load(input_queue_image::policy_enabled)!=0) {
            auto hook=state.keyboard_hook();
            if(hook!=0) {
                if(!state.unhook) throw std::invalid_argument("keyboard unhook bridge required");
                state.unhook(state,hook,state.user);
                state.set_keyboard_hook(0);
            }
            hook=state.mouse_hook();
            if(hook!=0) {
                if(!state.unhook) throw std::invalid_argument("mouse unhook bridge required");
                state.unhook(state,hook,state.user);
                state.set_mouse_hook(0);
            }
        }
        std::fill(state.raw_keys.begin(),state.raw_keys.end(),std::byte{0});
        if(!state.default_procedure)
            throw std::invalid_argument("default window procedure bridge required");
        result=state.default_procedure(state,window,message,wparam,lparam,state.user);
        return 1;
    }

    if(!state.default_procedure)
        throw std::invalid_argument("default window procedure bridge required");
    result=state.default_procedure(state,window,message,wparam,lparam,state.user);
    state.set_active(1);
    if(dispatch.load(input_queue_image::policy_enabled)==0) return 1;

    auto hook=state.keyboard_hook();
    if(hook==0) {
        if(!state.get_module || !state.set_hook)
            throw std::invalid_argument("keyboard hook installation bridges required");
        const auto module=state.get_module(state,state.user);
        hook=state.set_hook(state,2,0x583e60,module,0,state.user);
        state.set_keyboard_hook(hook);
    }
    hook=state.mouse_hook();
    if(hook==0) {
        if(!state.get_module || !state.set_hook)
            throw std::invalid_argument("mouse hook installation bridges required");
        const auto module=state.get_module(state,state.user);
        hook=state.set_hook(state,0x0d,0x583f50,module,0,state.user);
        state.set_mouse_hook(hook);
    }
    return 1;
}
}  // namespace mco
