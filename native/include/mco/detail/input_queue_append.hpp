#pragma once
#include "mco/input_key_queue.hpp"
#include <bit>
namespace mco::detail {
inline void input_queue_append(InputKeyQueue& state,std::uint32_t code,std::uint32_t character,
                               std::byte extended,bool late_flag) {
    const auto slot=state.load(input_queue_image::write_cursor);
    state.synchronize(true);
    auto event=state.event(slot);
    // Captured after enter, before event stores (including cursor-alias cases).
    const auto cursor=state.load(input_queue_image::write_cursor);
    event[input_queue_event::character]=static_cast<std::byte>(character&255u);
    event[input_queue_event::character+1]=static_cast<std::byte>((character>>8)&255u);
    event[input_queue_event::scan]=static_cast<std::byte>(code&255u);
    if(!late_flag) event[input_queue_event::extended]=extended;
    const auto capacity=std::bit_cast<std::int32_t>(state.load(input_queue_image::capacity));
    if(capacity<=0) throw std::invalid_argument("input queue capacity must be positive at division");
    const auto next=std::bit_cast<std::int32_t>(cursor+1u)%capacity;
    const auto head=state.load(input_queue_image::read_cursor);
    if(late_flag) event[input_queue_event::extended]=extended;
    state.store(input_queue_image::write_cursor,std::bit_cast<std::uint32_t>(next));
    if(head==std::bit_cast<std::uint32_t>(next)) {
        const auto advanced=std::bit_cast<std::int32_t>(head+1u)%capacity;
        state.store(input_queue_image::read_cursor,std::bit_cast<std::uint32_t>(advanced));
    }
    state.synchronize(false);
}
}
