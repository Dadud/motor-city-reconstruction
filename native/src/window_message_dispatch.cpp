#include "mco/window_message_dispatch.hpp"
#include <stdexcept>
#include <bit>
#include "mco/detail/window_dispatch_search.hpp"

namespace mco {

// Decompiled pseudocode of 0x583210, kept as the implementation draft.
// The oracle against the original, not this text, decides correctness.


std::uint32_t window_message_dispatch(WindowDispatchState &state, std::uint32_t window, std::uint32_t message, std::uint32_t wparam, std::uint32_t lparam, std::uint32_t result_identity) {
    if(state.enabled==0) return 0;
    state.synchronize(true);
    std::uint32_t result=0;
    if(const auto handler=detail::window_dispatch_search(state,message)) {
        if(!state.invoke) throw std::invalid_argument("window handler bridge required");
        result=state.invoke(state,*handler,0xacada0,window,message,wparam,lparam,result_identity,state.user);
    }
    // The callback may have replaced the original synchronizer identity.
    state.synchronize(false);
    return result;
}

}  // namespace mco
