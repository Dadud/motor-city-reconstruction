#include "mco/copy_line_segment.hpp"
#include <stdexcept>

namespace mco {
std::uint32_t copy_line_segment(std::span<std::byte> destination,
                                 std::span<const std::byte> source,
                                 std::int32_t inclusive_limit) {
    std::size_t copied = 0;
    // INC ESI / signed JLE never exceeds INT_MAX after counter wrap. For
    // that limit only newline (or an invalid span) ends the original loop.
    while (inclusive_limit >= 0 && (inclusive_limit == 0x7fffffff
           || copied <= static_cast<std::uint32_t>(inclusive_limit))) {
        if (copied >= source.size()) throw std::invalid_argument("line source truncated");
        const auto value = source[copied];
        if (value == std::byte{10}) break;
        if (copied >= destination.size()) throw std::invalid_argument("line destination truncated");
        destination[copied] = value;
        ++copied;
    }
    if (copied >= destination.size()) throw std::invalid_argument("line terminator outside destination");
    destination[copied] = std::byte{0};
    // Even after a limit stop or a negative limit, the original skips one.
    return static_cast<std::uint32_t>(copied+1u);
}
}
