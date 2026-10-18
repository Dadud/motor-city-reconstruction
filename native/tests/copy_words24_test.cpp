#include "mco/copy_words24.hpp"
#include <stdexcept>
int main() {
    std::array<std::byte,32> backing{};
    for (unsigned k = 0; k < 32; ++k) backing[k] = static_cast<std::byte>((k/4+1)*0x11);
    const auto returned = mco::copy_words24(std::span<std::byte,24>(backing.data()+4,24),
                      std::span<const std::byte,24>(backing.data(),24));
    if (returned.data() != backing.data()+4
        || backing[20] != std::byte{0x11} || backing[24] != std::byte{0x66})
        throw std::runtime_error("overlap must preserve the final staged pair");
}
