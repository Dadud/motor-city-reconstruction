#include "window_registration_cases.hpp"
#include <stdexcept>
int main() {
    std::array<std::byte,input_queue_image::size> globals{};
    window_dispatch_cases::Fixture f{0,0x12345678,7,0x100,{},{}};
    mco::WindowDispatchState state{globals,0,f.sync,f.invoke,&f,window_registration_cases::create};
    if(mco::window_handler_register(state,0x104,0x70009100)!=1 ||
       state.load(input_queue_image::dispatch_synchronizer)!=7 || f.logs[0][0]!=0)
        throw std::runtime_error("first registration/creation changed");
    if(mco::window_handler_register(state,0x100,0x70009000)!=1 ||
       state.load(input_queue_image::message_handlers)!=0x100 ||
       state.load(input_queue_image::message_handler_count)!=2)
        throw std::runtime_error("insertion order changed");
    if(mco::window_handler_register(state,0x100,0x70009100)!=1 ||
       state.load(input_queue_image::message_handler_count)!=2)
        throw std::runtime_error("replacement appended an entry");
    state.enabled=1;
    if(mco::window_message_dispatch(state,7,0x100,0,0,0)!=8)
        throw std::runtime_error("replaced handler not dispatched");
    if(mco::window_handler_register(state,0x100,0)!=1 ||
       state.load(input_queue_image::message_handler_count)!=1 ||
       state.load(input_queue_image::message_handlers)!=0x104 ||
       state.load(input_queue_image::message_handlers+8)!=0x7fffffff)
        throw std::runtime_error("sentinel removal changed");
    if(mco::window_handler_register(state,0x100,0)!=0)
        throw std::runtime_error("missing removal succeeded");
    state.store(input_queue_image::message_handler_count,128);
    for(unsigned i=0;i<128;++i) {
        state.store(input_queue_image::message_handlers+i*8,0x100+i);
        state.store(input_queue_image::message_handlers+i*8+4,0x70009000);
    }
    if(mco::window_handler_register(state,0x999,0x70009100)!=0 ||
       mco::window_handler_register(state,0x100,0x70009100)!=1 ||
       state.load(input_queue_image::message_handler_count)!=128)
        throw std::runtime_error("full table insertion/replacement changed");
}
