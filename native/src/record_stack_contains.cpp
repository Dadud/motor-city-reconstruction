#include "mco/record_stack_contains.hpp"
#include <stdexcept>
#include "mco/layouts.hpp"
#include "mco/detail/byte_words.hpp"

namespace mco {
std::uint32_t record_stack_contains(std::span<const std::byte> records,
                                     std::uint32_t base, std::uint32_t cursor,
                                     std::uint32_t identifier) {
    if (records.size() > (std::uint64_t(1)<<32)-base)
        throw std::invalid_argument("record span crosses original address wrap");
    std::size_t offset = 0;
    for (;;) {
        if (detail::read_word(records, offset+state_record::identifier) == identifier)
            return 1;
        const auto next = offset+state_record::size;
        if (std::uint64_t(base)+next > 0xffffffffu)
            throw std::invalid_argument("record traversal crosses original address wrap");
        if (std::uint64_t(base)+next > cursor) return 0;
        offset = next;
    }
}
}
