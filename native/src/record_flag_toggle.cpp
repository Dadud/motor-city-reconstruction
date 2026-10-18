#include "mco/record_flag_toggle.hpp"
#include <stdexcept>
#include "mco/layouts.hpp"
#include "mco/detail/byte_words.hpp"

namespace mco {
void record_flag_toggle(std::span<std::byte> record) {
    const auto value = detail::read_word(record, state_record::flags);
    detail::write_word(record, state_record::flags, value ^ 0x100u);
}
}
