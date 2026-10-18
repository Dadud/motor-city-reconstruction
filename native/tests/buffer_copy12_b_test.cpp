#include "mco/buffer_copy12_b.hpp"
#include <stdexcept>
#include <array>
int main() {
    std::array<std::byte,12> destination{};
    std::array<std::byte,12> source{};
    for (unsigned k = 0; k < 12; ++k)
        source[k] = static_cast<std::byte>(0x40 + k);
    mco::buffer_copy12_b(destination, source);
    for (unsigned k = 0; k < 12; ++k)
        if (destination[k] != source[k])
            throw std::runtime_error("copy regression");
    return 0;
}
