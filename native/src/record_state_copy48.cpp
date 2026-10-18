#include "mco/record_state_copy48.hpp"
#include <stdexcept>
#include "mco/layouts.hpp"
#include "mco/detail/byte_words.hpp"

namespace mco {
void record_state_copy48(std::span<std::byte,48> destination,
                         std::span<const std::byte> record) {
    const auto start = state_record::exported_state;
    // Stage the second and third words together, exactly as the original.
    detail::write_word(destination, 0, detail::read_word(record, start));
    const auto second = detail::read_word(record, start+4);
    const auto third = detail::read_word(record, start+8);
    detail::write_word(destination, 4, second);
    detail::write_word(destination, 8, third);
    // The original REP MOVSD assumes the caller's direction flag is clear.
    for (unsigned k = 3; k < 12; ++k) {
        const auto word = detail::read_word(record, start+k*4);
        detail::write_word(destination, k*4, word);
    }
}
}
