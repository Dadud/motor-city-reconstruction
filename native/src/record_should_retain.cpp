#include "mco/record_should_retain.hpp"
#include <bit>
#include <stdexcept>
#include "mco/detail/byte_words.hpp"
#include "mco/layouts.hpp"
#include "mco/record_handler.hpp"

namespace mco {
std::uint32_t record_should_retain(std::span<const std::byte> record,
                                         std::span<const std::byte> request,
                                         std::uint32_t tick) {
    const auto identifier = detail::read_word(request, record_request::identifier);
    const auto handler = record_handler(identifier);
    const bool special = handler == 0x42f630 || handler == 0x431ba0;
    const bool same = detail::read_word(record, state_record::identifier) == identifier;
    if (detail::read_word(request, record_request::override_match) != 0) return same ? 1u : 0u;
    if (same) {
        if (identifier == 14 || identifier == 22) return 1;
        return special && detail::read_word(record, state_record::parameter)
            == detail::read_word(request, record_request::parameter) ? 1u : 0u;
    }
    const auto until = std::bit_cast<std::int32_t>(detail::read_word(record, state_record::retain_until));
    if (until <= std::bit_cast<std::int32_t>(tick)) return 0;
    return special ? 0u : 1u;
}
}
