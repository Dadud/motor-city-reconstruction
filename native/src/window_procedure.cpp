#include "mco/window_procedure.hpp"
#include <stdexcept>
#include "mco/detail/window_dispatch_search.hpp"

namespace mco {

// Decompiled pseudocode of 0x583290, kept as the implementation draft.
// The oracle against the original, not this text, decides correctness.


std::uint32_t window_procedure(WindowDispatchState &state, const WindowProcedureBridge &bridge, std::uint32_t window, std::uint32_t message, std::uint32_t wparam, std::uint32_t lparam) {
    std::uint32_t local_result=0,handled=0;
    if(state.enabled!=0) {
        state.synchronize(true);
        if(const auto handler=detail::window_dispatch_search(state,message)) {
            if(!bridge.invoke) throw std::invalid_argument("window procedure handler bridge required");
            handled=bridge.invoke(state,*handler,0xacada0,window,message,wparam,lparam,local_result,bridge.user);
        }
        state.synchronize(false);
        if(handled!=0) return local_result;
    }
    if(!bridge.default_procedure) throw std::invalid_argument("default window procedure bridge required");
    return bridge.default_procedure(state,window,message,wparam,lparam,bridge.user);
}

}  // namespace mco
