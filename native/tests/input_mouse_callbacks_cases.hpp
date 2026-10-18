#pragma once
#include "mco/input_mouse_callbacks.hpp"
#include "input_mouse_lifetime_cases.hpp"
namespace input_mouse_callbacks_cases {
using namespace mco;
inline void compare(std::istream& in){
    const auto mode=cell_io::read(in),script=cell_io::read(in),seed=cell_io::read(in);
    input_mouse_lifetime_cases::Fixture f;f.config={0,0,script,seed};
    std::array<std::uint32_t,15> words{};for(auto& v:words)v=cell_io::read(in);
    auto width=cell_io::read(in),height=cell_io::read(in);mco::InputMouseLifetimeState lifetime{words,width,height};
    auto enabled=cell_io::read(in),button_callback=cell_io::read(in);
    std::array<std::byte,mouse_input_image::size> image{};
    for(unsigned i=0;i<7;++i)detail::write_word(image,i*4,cell_io::read(in));
    auto x=cell_io::read(in),y=cell_io::read(in),buttons=cell_io::read(in),wheel=cell_io::read(in),counter=cell_io::read(in);
    std::array<std::uint32_t,3> ids{};for(auto& v:ids)v=cell_io::read(in);
    std::array<std::byte,input_queue_image::size> globals{};
    detail::write_word(globals,input_queue_image::target_window,cell_io::read(in));
    const auto active=cell_io::read(in),window_id=cell_io::read(in),wparam=cell_io::read(in);
    mco::WindowDispatchState window{globals,1};mco::MouseInputState mouse{window,image,enabled,button_callback};
    mco::InputMouseGeometryState geometry{mouse,x,y};mco::InputMouseCallbacks state{lifetime,geometry,wheel,counter,buttons,ids};
    for(unsigned i=0;i<6;++i)f.tables[i]=(seed+i)%2;
    std::uint32_t result=0;
    switch(mode){
    case 0:mco::input_mouse_driver_setup(state);break;
    case 1:result=mco::input_mouse_wheel(state,active,window_id,wparam);break;
    case 2:mco::input_mouse_shutdown(state,f.platform());break;
    case 3:result=mco::input_mouse_report(state);break;
    case 4:mco::input_mouse_counter_increment(state);break;
    case 5:mco::input_mouse_counter_decrement(state);break;
    default:throw std::invalid_argument("mouse callbacks mode");
    }
    cell_io::emit(result);cell_io::emit(words);cell_io::emit(width);cell_io::emit(height);
    cell_io::emit(mouse.enabled);cell_io::emit(mouse.button_callback);
    for(unsigned i=0;i<7;++i)cell_io::emit(detail::read_word(image,i*4));
    cell_io::emit(x);cell_io::emit(y);cell_io::emit(buttons);cell_io::emit(wheel);cell_io::emit(counter);cell_io::emit(ids);
    cell_io::emit(window.load(input_queue_image::target_window));cell_io::emit(f.tables);
    cell_io::emit(static_cast<std::uint32_t>(f.logs.size()));for(const auto& row:f.logs)cell_io::emit(row);
}
}
