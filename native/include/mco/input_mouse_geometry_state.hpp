#pragma once
#include "mco/input_mouse_update.hpp"
#include "mco/input_cursor_warp.hpp"
namespace mco {
// Separate observed words 0x8c4600/04 alias the requested/clamped position.
struct InputMouseGeometryState {
    MouseInputState& mouse;
    std::uint32_t& position_x;
    std::uint32_t& position_y;
};
// Context helpers retain their observed order. The unresolved local context
// object's bytes and its platform behavior remain the adapter's responsibility.
using InputMouseGeometryInvoke=std::uint32_t (*)(InputMouseGeometryState&,
    std::uint32_t identity,std::uint32_t argument,void* user);
struct InputMouseGeometryPlatform {InputMouseGeometryInvoke invoke{};void* user{};};
}
