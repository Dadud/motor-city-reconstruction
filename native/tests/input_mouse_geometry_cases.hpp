#pragma once
#include "mouse_input_cases.hpp"
#include "mco/input_mouse_geometry.hpp"
namespace input_mouse_geometry_cases {
struct Script {
    mouse_input_cases::Fixture fixture;
    std::uint32_t first_query{},second_query{},query_count{};
    static std::uint32_t invoke(mco::InputMouseGeometryState& s,std::uint32_t id,std::uint32_t argument,void* user) {
        auto& f=*static_cast<Script*>(user);
        f.fixture.observe(9,id,argument,s.position_x,s.position_y);
        if(id==0x6be930)return f.query_count++ ? f.second_query:f.first_query;
        return 0;
    }
};
inline void compare(std::istream& input) {
    const auto operation=cell_io::read(input);
    Script script;
    script.first_query=cell_io::read(input);script.second_query=cell_io::read(input);
    auto& f=script.fixture;
    f.mask=cell_io::read(input);f.value=cell_io::read(input);f.success=cell_io::read(input);
    f.cx=cell_io::read(input);f.cy=cell_io::read(input);
    const auto enabled=cell_io::read(input),callback=cell_io::read(input);
    auto px=cell_io::read(input),py=cell_io::read(input);
    std::array<std::uint32_t,4> args;for(auto& v:args)v=cell_io::read(input);
    auto globals=cell_io::image<input_queue_image::size>(input);
    auto image=cell_io::image<mouse_input_image::size>(input);
    mco::WindowDispatchState window{globals,1,f.sync,nullptr,&f};
    mco::MouseInputState mouse{window,image,enabled,callback};f.mouse=&mouse;
    const mco::MousePlatformBridge platform{f.convert,f.position,f.cursor,f.notify,&f};
    mco::InputMouseGeometryState state{mouse,px,py};
    if(operation==0)mco::input_mouse_set_bounds(state,platform,args[0],args[1],args[2],args[3]);
    else if(operation==1)mco::input_mouse_set_position(state,platform,{Script::invoke,&script},args[0],args[1]);
    else throw std::invalid_argument("mouse geometry operation");
    cell_io::emit(px);cell_io::emit(py);cell_io::emit(mouse.enabled);cell_io::emit(mouse.button_callback);
    cell_io::emit(globals);cell_io::emit(image);
    cell_io::emit(static_cast<std::uint32_t>(f.logs.size()));for(const auto& row:f.logs)cell_io::emit(row);
}
}
