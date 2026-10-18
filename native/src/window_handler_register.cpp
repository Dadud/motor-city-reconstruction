#include "mco/window_handler_register.hpp"
#include <stdexcept>
#include "mco/detail/window_dispatch_search.hpp"
#include "mco/detail/window_dispatch_sort.hpp"

namespace mco {

// Decompiled pseudocode of 0x582e40, kept as the implementation draft.
// The oracle against the original, not this text, decides correctness.


std::uint32_t window_handler_register(WindowDispatchState &state, std::uint32_t message, std::uint32_t handler) {
    using namespace input_queue_image;
    if(state.load(dispatch_synchronizer)==0) {
        if(!state.create_sync) throw std::invalid_argument("window synchronizer creation bridge required");
        state.store(dispatch_synchronizer,state.create_sync(state,state.user));
    }
    state.synchronize(true);
    const auto index=detail::window_dispatch_find(state,message);
    const auto count=state.load(message_handler_count);
    std::uint32_t result=0;
    if(!index) {
        if(handler!=0 && count<128) {
            state.store(message_handlers+count*8,message);state.store(message_handlers+count*8+4,handler);
            state.store(message_handler_count,count+1);
            detail::window_dispatch_sort(state,count+1);result=1;
        }
    } else {
        if(handler==0) {
            state.store(message_handlers+*index*8,0x7fffffffu);
            detail::window_dispatch_sort(state,count);
            state.store(message_handler_count,count-1);
        } else state.store(message_handlers+*index*8+4,handler);
        result=1;
    }
    state.synchronize(false);
    return result;
}

}  // namespace mco
