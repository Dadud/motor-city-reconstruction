#include "mco/input_key_release.hpp"
#include <stdexcept>
#include "mco/layouts.hpp"
namespace mco {
std::uint32_t input_key_release(std::span<std::byte> keys,
    std::span<const std::byte,key_remap_image::size> remap,std::uint32_t remap_present,
    std::uint32_t enabled,std::uint32_t message_window,std::uint32_t target_window,
    std::uint32_t message_bits) {
    if(enabled==0 || message_window!=target_window) return 0;
    auto code=(message_bits>>16)&127u;
    if(remap_present!=0) code=std::to_integer<std::uint32_t>(remap[code]);
    if(code==42 || code==54) {
        if(keys.size()<=54) throw std::invalid_argument("shift release outside key image");
        keys[54]=std::byte{};keys[42]=std::byte{};
    } else {
        if(code>=keys.size()) throw std::invalid_argument("release outside key image");
        keys[code]=std::byte{};
    }
    return 0;
}
}
