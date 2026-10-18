#include "mco/input_key_query.hpp"
#include "mco/layouts.hpp"
#include "mco/input_key_raw.hpp"
#include <stdexcept>
namespace mco {
std::uint32_t input_key_query(std::span<const std::byte,key_state_image::size> keys,
    std::span<std::byte> latches,std::uint32_t code,std::uint32_t press_only) {
    if(code>=latches.size() || (code & 0x80000000u))
        throw std::invalid_argument("key latch outside supplied nonnegative window");
    const auto raw=input_key_raw(keys,code);
    const auto masked=latches[code] & static_cast<std::byte>(raw);
    latches[code]=masked;
    if(press_only==0) return raw!=0;
    if(raw!=0 && masked==std::byte{}) {
        latches[code]=std::byte{255};
        return 1;
    }
    return 0;
}
}
