#include "mco/record_identifier.hpp"
#include <stdexcept>
#include "mco/layouts.hpp"
#include "mco/detail/byte_words.hpp"

namespace mco {
std::uint32_t record_identifier(std::span<const std::byte> record) {
    return detail::read_word(record, state_record::identifier);
}
}
