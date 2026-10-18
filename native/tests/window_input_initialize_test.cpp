#include "window_initialization_cases.hpp"
#include "mco/detail/window_dispatch_search.hpp"
#include <stdexcept>
int main() {
    std::array<std::byte,input_queue_image::size> globals{};
    window_dispatch_cases::Fixture f{0,0,0x1000,0x100,{},{}};
    f.creation_stride=0x100;
    mco::WindowDispatchState state{globals,0,f.sync,nullptr,&f,window_registration_cases::create};
    state.store(input_queue_image::capacity,1);
    state.store(input_queue_image::read_cursor,7);state.store(input_queue_image::write_cursor,9);
    if(mco::window_input_initialize(state)!=1 || state.load(input_queue_image::initialized)!=1 ||
       state.load(input_queue_image::capacity)!=32 || state.load(input_queue_image::read_cursor)!=0 ||
       state.load(input_queue_image::write_cursor)!=0 || state.load(input_queue_image::synchronizer)!=0x1000 ||
       state.load(input_queue_image::dispatch_synchronizer)!=0x1100 || f.creation_calls!=2 ||
       state.load(input_queue_image::message_handler_count)!=28 ||
       mco::detail::window_dispatch_search(state,0x100)!=0x584450 ||
       mco::detail::window_dispatch_search(state,0x105)!=0x584610)
        throw std::runtime_error("initial queue or handler installation changed");
    const auto before=globals;const auto log_count=f.logs.size();
    if(mco::window_input_initialize(state)!=0 || globals!=before || f.logs.size()!=log_count)
        throw std::runtime_error("reinitialization was not guarded");
    state.store(input_queue_image::initialized,0);state.store(input_queue_image::message_handler_count,128);
    for(unsigned i=0;i<128;++i) {
        state.store(input_queue_image::message_handlers+i*8,0x1000+i);
        state.store(input_queue_image::message_handlers+i*8+4,0x1234);
    }
    if(mco::window_input_initialize(state)!=1 || state.load(input_queue_image::initialized)!=1 ||
       state.load(input_queue_image::message_handler_count)!=128)
        throw std::runtime_error("initializer invented registration-failure propagation");
}
