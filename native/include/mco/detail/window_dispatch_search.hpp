#pragma once
#include "mco/window_dispatch_state.hpp"
#include <bit>
#include <optional>
namespace mco::detail {
inline std::optional<std::uint32_t> window_dispatch_find(const WindowDispatchState& state,std::uint32_t message) {
    auto count=state.load(input_queue_image::message_handler_count);
    if(count>128) throw std::invalid_argument("window handler table exceeds supplied image");
    std::uint32_t low=0;
    while(count!=0) {
        // Original lower midpoint and wrapping signed subtraction comparator.
        const auto middle=low+(count-1)/2;
        const auto offset=input_queue_image::message_handlers+middle*8;
        const auto difference=std::bit_cast<std::int32_t>(message-state.load(offset));
        if(difference==0) return middle;
        if(difference<0) count=(count&1u) ? count/2 : count/2-1;
        else {low=middle+1;count/=2;}
    }
    return std::nullopt;
}
inline std::optional<std::uint32_t> window_dispatch_search(const WindowDispatchState& state,std::uint32_t message) {
    if(const auto index=window_dispatch_find(state,message))
        return state.load(input_queue_image::message_handlers+*index*8+4);
    return std::nullopt;
}
}
