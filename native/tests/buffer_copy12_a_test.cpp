#include "mco/buffer_copy12_a.hpp"
#include <stdexcept>
#include <array>
int main() {
    std::array<std::byte,12> destination{};
    std::array<std::byte,12> source{};
    for (unsigned k = 0; k < 12; ++k)
        source[k] = static_cast<std::byte>(k + 1);
    mco::buffer_copy12_a(destination, source);
    for (unsigned k = 0; k < 12; ++k)
        if (destination[k] != source[k])
            throw std::runtime_error("copy regression");
    return 0;
}
