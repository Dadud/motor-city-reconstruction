#include "mco/camera_context_special.hpp"
#include "mco/detail/byte_words.hpp"
#include "mco/layouts.hpp"
namespace mco {
std::uint32_t camera_context_special(std::span<const std::byte, 12> context) {
    const auto kind = detail::read_word(context, camera_context::kind);
    if (kind == 0x12u) return 1;
    const auto secondary = detail::read_word(context, camera_context::secondary);
    return secondary == 0x17u || secondary == 0x18u;
}
}
