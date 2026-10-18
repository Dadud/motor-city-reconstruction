#include "mco/record_pair_match.hpp"
#include <bit>
#include <stdexcept>
#include "mco/detail/byte_words.hpp"

namespace mco {
std::uint32_t record_pair_match(std::span<const std::byte> pairs,
                                 std::uint32_t first, std::uint32_t second) {
    for (std::size_t offset = 0;; offset += 8) {
        const auto left = detail::read_word(pairs, offset);
        if (left == 0xffffffffu) return 0;
        const auto right = detail::read_word(pairs, offset+4);
        if ((left == first && right == second) || (left == second && right == first)) return 1;
    }
}
}
