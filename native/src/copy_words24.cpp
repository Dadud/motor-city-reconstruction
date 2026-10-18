#include "mco/copy_words24.hpp"
#include <stdexcept>
#include "mco/detail/byte_words.hpp"

namespace mco {
std::span<std::byte,24> copy_words24(std::span<std::byte,24> destination,
                  std::span<const std::byte,24> source) {
    for (unsigned k = 0; k < 4; ++k) {
        const auto word = detail::read_word(source, k*4);
        detail::write_word(destination, k*4, word);
    }
    const auto fourth = detail::read_word(source, 16);
    const auto fifth = detail::read_word(source, 20);
    detail::write_word(destination, 16, fourth);
    detail::write_word(destination, 20, fifth);
    return destination;
}
}
