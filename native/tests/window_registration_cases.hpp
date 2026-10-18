#pragma once
#include "window_dispatch_cases.hpp"
#include "mco/window_handler_register.hpp"
namespace window_registration_cases {
inline std::uint32_t create(mco::WindowDispatchState& state,void* user) {
    auto& f=*static_cast<window_dispatch_cases::Fixture*>(user);
    using namespace input_queue_image;
    f.logs.push_back({0,0,state.enabled,state.load(message_handler_count),state.load(dispatch_synchronizer),
                     state.load(message_handlers),state.load(message_handlers+4),0});
    if(f.mask&256) state.store(message_handler_count,0);
    return f.retval+f.creation_calls++*f.creation_stride;
}
inline void compare(std::istream& input) {
    const auto enabled=cell_io::read(input),mask=cell_io::read(input),value=cell_io::read(input),created=cell_io::read(input);
    const auto message=cell_io::read(input),handler=cell_io::read(input);
    auto globals=cell_io::image<input_queue_image::size>(input);
    window_dispatch_cases::Fixture f{mask,value,created,message,{},{}};
    mco::WindowDispatchState state{globals,enabled,f.sync,nullptr,&f,create};
    cell_io::emit(mco::window_handler_register(state,message,handler));
    cell_io::emit(state.enabled);cell_io::emit(globals);
    cell_io::emit(static_cast<std::uint32_t>(f.logs.size()));
    for(const auto& row:f.logs) cell_io::emit(row);
}
}
