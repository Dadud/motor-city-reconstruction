#pragma once
#include "window_registration_cases.hpp"
#include "mco/window_input_initialize.hpp"
namespace window_initialization_cases {
inline void compare(std::istream& input) {
    const auto enabled=cell_io::read(input),mask=cell_io::read(input),value=cell_io::read(input);
    const auto created=cell_io::read(input),stride=cell_io::read(input);
    auto globals=cell_io::image<input_queue_image::size>(input);
    window_dispatch_cases::Fixture f{mask,value,created,0x100,{},{}};
    f.creation_stride=stride;
    mco::WindowDispatchState state{globals,enabled,f.sync,nullptr,&f,window_registration_cases::create};
    cell_io::emit(mco::window_input_initialize(state));cell_io::emit(state.enabled);cell_io::emit(globals);
    cell_io::emit(static_cast<std::uint32_t>(f.logs.size()));
    for(const auto& row:f.logs) cell_io::emit(row);
}
}
