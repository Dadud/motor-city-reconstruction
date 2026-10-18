#include "mco/selection_state_normalize.hpp"
#include "mco/detail/byte_words.hpp"
#include <bit>
#include "mco/layouts.hpp"

namespace mco {
std::uint32_t selection_state_normalize(std::span<std::byte, 24> state) {
    const auto signed_word = [&](std::size_t index) {
        return std::bit_cast<std::int32_t>(detail::read_word(state, index*4));
    };
    const auto store = [&](std::size_t index, std::int32_t value) {
        detail::write_word(state, index*4, std::bit_cast<std::uint32_t>(value));
    };
    const auto fifth = signed_word(camera_selection::selected_index/4);
    store(camera_selection::selected_index/4, fifth < 0 ? 0 : fifth % 5);
    const auto sixth = signed_word(camera_selection::selected_slot/4);
    store(camera_selection::selected_slot/4, sixth < 0 ? 0 : sixth % 4);
    std::int32_t quotient = 0;
    for (std::size_t index = 0; index != 4; ++index) {
        const auto value = signed_word(index);
        quotient = value / 5;
        store(index, value % 5);
    }
    if (signed_word(0) == 0) store(0, 1);
    return std::bit_cast<std::uint32_t>(quotient);
}
}
