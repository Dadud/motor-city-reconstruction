#include "mco/input_character.hpp"
#include <stdexcept>
#include "mco/detail/input_queue_append.hpp"

namespace mco {

// Decompiled pseudocode of 0x584370, kept as the implementation draft.
// The oracle against the original, not this text, decides correctness.


std::uint32_t input_character(InputKeyQueue &state, std::uint32_t enabled, std::uint32_t window, std::uint32_t message, std::uint32_t character, std::uint32_t message_bits) {
    (void)message;
    if(enabled==0 || window!=state.load(input_queue_image::target_window)) return 1;
    const auto capacity=std::bit_cast<std::int32_t>(state.load(input_queue_image::capacity));
    if(capacity<0) throw std::invalid_argument("negative initial character queue capacity");
    auto repeat=message_bits&65535u;
    if(repeat>static_cast<std::uint32_t>(capacity)) repeat=static_cast<std::uint32_t>(capacity);
    const auto code=(message_bits>>16)&127u;
    const auto extended=static_cast<std::byte>((message_bits>>24)&1u);
    while(repeat--!=0) detail::input_queue_append(state,code,character,extended,false);
    return 1;
}

}  // namespace mco
