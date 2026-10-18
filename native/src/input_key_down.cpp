#include "mco/input_key_down.hpp"
#include "mco/input_key_translate.hpp"
#include <bit>
#include "mco/detail/input_queue_append.hpp"
#include <stdexcept>
namespace mco {
std::uint32_t input_key_down(InputKeyQueue& state,std::span<const std::byte,128> remap,
    std::uint32_t enabled,std::uint32_t window,std::uint32_t message,
    std::uint32_t key,std::uint32_t message_bits) {
    if(enabled==0 || window!=state.load(input_queue_image::target_window)) return 1;
    const auto initial_capacity=std::bit_cast<std::int32_t>(state.load(input_queue_image::capacity));
    if(initial_capacity<0) throw std::invalid_argument("negative initial input queue capacity");
    auto repeat=message_bits&0xffffu;
    if(repeat>static_cast<std::uint32_t>(initial_capacity)) repeat=static_cast<std::uint32_t>(initial_capacity);
    auto code=(message_bits>>16)&127u;
    state.store(input_queue_image::last_code,code);
    if(state.load(input_queue_image::remap)!=0) {
        code=std::to_integer<std::uint32_t>(remap[code]);
        state.store(input_queue_image::last_code,code);
    }
    const bool translated=state.load(input_queue_image::raw_mode)==0;
    state.keys[code]=std::byte{1};
    const auto character=translated ? input_key_translate(message,key) : 0u;
    if(translated && character==0) return 0;
    const auto extended=static_cast<std::byte>((message_bits>>24)&1u);
    while(repeat!=0) {
        detail::input_queue_append(state,code,character,extended,translated);
        --repeat;
        if(repeat!=0) code=state.load(input_queue_image::last_code);
    }
    return 1;
}
}
