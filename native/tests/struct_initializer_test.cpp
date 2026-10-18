#include "mco/struct_initializer.hpp"
#include <array>
#include <stdexcept>
int main() {
    std::array<std::byte,4> count{};
    count.fill(static_cast<std::byte>(0xee));
    std::array<std::byte,12> state{};
    state.fill(static_cast<std::byte>(0xee));
    mco::struct_initializer(count, state);
    auto word = [](auto& image, size_t offset) {
        return static_cast<std::uint32_t>(image[offset])
            | static_cast<std::uint32_t>(image[offset+1]) << 8
            | static_cast<std::uint32_t>(image[offset+2]) << 16
            | static_cast<std::uint32_t>(image[offset+3]) << 24; };
    if (word(count, 0) != 0x1e)
        throw std::runtime_error("count image must take 0x1e");
    if (word(state, 0) != 0x42a00000u)
        throw std::runtime_error("state must take the float constant");
    if (word(state, 4) != 0 || word(state, 8) != 0)
        throw std::runtime_error("state tail must zero");
    return 0;
}
