#include "mco/record_signed_negate.hpp"
#include <stdexcept>
#include "mco/layouts.hpp"
#include "mco/detail/byte_words.hpp"

namespace mco {
void record_signed_negate(std::span<std::byte> record) {
    const auto value = detail::read_word(record, state_record::signed_word);
    detail::write_word(record, state_record::signed_word, 0u-value);
}
}
