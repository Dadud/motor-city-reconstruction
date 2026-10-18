#include "mco/window_input_initialize.hpp"
#include <stdexcept>
#include "mco/window_handler_register.hpp"
#include <utility>

namespace mco {

// Decompiled pseudocode of 0x583c30, kept as the implementation draft.
// The oracle against the original, not this text, decides correctness.


std::uint32_t window_input_initialize(WindowDispatchState &state) {
    using namespace input_queue_image;
    if(state.load(initialized)!=0) return 0;
    if(!state.create_sync) throw std::invalid_argument("input synchronizer creation bridge required");
    state.store(synchronizer,state.create_sync(state,state.user));
    state.store(capacity,32);state.store(read_cursor,0);state.store(write_cursor,0);
    constexpr std::array<std::pair<std::uint32_t,std::uint32_t>,28> handlers{{
        {1,0x583e00},{0x1c,0x584050},{6,0x584070},{5,0x584310},{3,0x584310},
        {0x10,0x5841b0},{2,0x584210},{0xf,0x584730},{0x14,0x5847c0},
        {0x1a,0x584290},{0x112,0x584250},{0x466,0x5841e0},{0x102,0x584370},
        {0x100,0x584450},{0x104,0x584450},{0x101,0x584610},{0x105,0x584610},
        {0x201,0x584670},{0x207,0x584670},{0x204,0x584670},{0x203,0x584670},
        {0x209,0x584670},{0x206,0x584670},{0x202,0x5846d0},{0x208,0x5846d0},
        {0x205,0x5846d0},{0x200,0x5846d0},{0x218,0x5847f0}
    }};
    for(const auto& [message,handler]:handlers) window_handler_register(state,message,handler);
    // Registration failures are ignored by the original initializer.
    state.store(initialized,1);
    return 1;
}

}  // namespace mco
