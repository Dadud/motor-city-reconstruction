#pragma once
#include "mco/input_mouse_geometry_state.hpp"
namespace mco {
void input_mouse_set_bounds(InputMouseGeometryState&,const MousePlatformBridge&,
    std::uint32_t minimum_x,std::uint32_t minimum_y,std::uint32_t maximum_x,std::uint32_t maximum_y);
void input_mouse_set_position(InputMouseGeometryState&,const MousePlatformBridge&,
    const InputMouseGeometryPlatform&,std::uint32_t x,std::uint32_t y);
}
