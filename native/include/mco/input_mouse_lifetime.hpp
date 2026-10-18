#pragma once
#include "mco/input_mouse_lifetime_state.hpp"
namespace mco {
// Original 0x6ef890. Complete initialization with explicit unresolved helpers.
std::uint32_t input_mouse_lifetime(InputMouseLifetimeState&,const InputMouseLifetimePlatform&,
                                  std::uint32_t temporary);
void input_mouse_bounds(InputMouseLifetimeState&,const InputMouseLifetimePlatform&,
                       std::span<const std::uint32_t,6> arguments);
}
