#pragma once
#include "mco/input_mouse_lifetime.hpp"
#include "mco/input_mouse_geometry.hpp"
namespace mco {
struct InputMouseCallbacks {
    InputMouseLifetimeState& lifetime;
    InputMouseGeometryState& geometry;
    std::uint32_t& wheel;
    std::uint32_t& counter;
    std::uint32_t& reported_buttons;
    std::array<std::uint32_t,3>& callback_ids;
};
void input_mouse_driver_setup(InputMouseCallbacks&);
std::uint32_t input_mouse_wheel(InputMouseCallbacks&,std::uint32_t enabled,
                                std::uint32_t window,std::uint32_t wparam);
void input_mouse_shutdown(InputMouseCallbacks&,const InputMouseLifetimePlatform&);
std::uint32_t input_mouse_report(InputMouseCallbacks&);
void input_mouse_counter_increment(InputMouseCallbacks&);
void input_mouse_counter_decrement(InputMouseCallbacks&);
}
