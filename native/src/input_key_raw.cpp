#include "mco/input_key_raw.hpp"
#include "mco/layouts.hpp"
#include <bit>
namespace mco {
std::uint32_t input_key_raw(std::span<const std::byte,key_state_image::size> keys,std::uint32_t code) {
    if(std::bit_cast<std::int32_t>(code)>=256) return 0;
    return std::to_integer<std::uint32_t>(keys[code & 127u]);
}
}
