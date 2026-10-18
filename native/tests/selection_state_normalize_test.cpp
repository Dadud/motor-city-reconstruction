#include "mco/selection_state_normalize.hpp"
#include "mco/detail/byte_words.hpp"
#include <array>
#include <stdexcept>

int main() {
    std::array<std::byte, 24> state{};
    const std::array<std::uint32_t, 6> input{0xfffffffbu, 0x80000000u,
        0x7fffffffu, 0xfffffff6u, 0xffffffffu, 0x7fffffffu};
    for (std::size_t i=0; i!=6; ++i) mco::detail::write_word(state, i*4, input[i]);
    const auto result = mco::selection_state_normalize(state);
    const std::array<std::uint32_t, 6> expected{1, 0xfffffffdu, 2, 0, 0, 3};
    if (result != 0xfffffffeu) throw std::runtime_error("fourth quotient lost");
    for (std::size_t i=0; i!=6; ++i)
        if (mco::detail::read_word(state, i*4) != expected[i])
            throw std::runtime_error("signed selection normalization changed");
}
