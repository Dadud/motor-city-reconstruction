#include "mco/input_mouse_geometry.hpp"
#include <bit>
#include <stdexcept>
namespace mco {
namespace {
std::uint32_t clamp(std::uint32_t value,std::uint32_t lower,std::uint32_t upper) {
    const auto v=std::bit_cast<std::int32_t>(value),lo=std::bit_cast<std::int32_t>(lower),hi=std::bit_cast<std::int32_t>(upper);
    return (v>lo?v:lo)<hi ? (v>lo?value:lower):upper;
}
std::uint32_t call(InputMouseGeometryState& state,const InputMouseGeometryPlatform& platform,
                   std::uint32_t identity,std::uint32_t argument=0) {
    if(!platform.invoke)throw std::invalid_argument("mouse geometry context bridge required");
    return platform.invoke(state,identity,argument,platform.user);
}
}
void input_mouse_set_bounds(InputMouseGeometryState& state,const MousePlatformBridge& platform,
    std::uint32_t minx,std::uint32_t miny,std::uint32_t maxx,std::uint32_t maxy){
    auto& m=state.mouse;
    m.store(mouse_input_image::minimum_x,minx);m.store(mouse_input_image::minimum_y,miny);
    m.store(mouse_input_image::maximum_x,maxx);m.store(mouse_input_image::maximum_y,maxy);
    const auto buttons=m.load(mouse_input_image::buttons);
    const auto y=m.load(mouse_input_image::y),x=m.load(mouse_input_image::x);
    input_mouse_update(m,platform,x,y,buttons,0);
}
void input_mouse_set_position(InputMouseGeometryState& state,const MousePlatformBridge& cursor,
                              const InputMouseGeometryPlatform& platform,std::uint32_t x,std::uint32_t y) {
    if(call(state,platform,0x6be930)==0)call(state,platform,0x8c4938,1);
    else {call(state,platform,0x7b54a0);call(state,platform,0x6cf1b0);}
    auto& mouse=state.mouse;
    state.position_x=clamp(x,mouse.load(mouse_input_image::minimum_x),mouse.load(mouse_input_image::maximum_x));
    state.position_y=clamp(y,mouse.load(mouse_input_image::minimum_y),mouse.load(mouse_input_image::maximum_y));
    mouse.store(mouse_input_image::y,state.position_y);mouse.store(mouse_input_image::x,state.position_x);
    input_cursor_warp(mouse.window,cursor,state.position_x,state.position_y);
    if(call(state,platform,0x6be930)==0)call(state,platform,0x8c4938,0);
    else call(state,platform,0x7b54d0);
}
}
