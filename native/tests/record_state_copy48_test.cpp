#include "mco/record_state_copy48.hpp"
#include <stdexcept>
int main() {
    std::array<std::byte,256> backing{};
    for (unsigned k = 12; k < 64; ++k) backing[k] = static_cast<std::byte>(((k-12)/4+1)*0x11);
    mco::record_state_copy48(std::span<std::byte,48>(backing.data()+16,48), backing);
    if (backing[20] != std::byte{0x11} || backing[24] != std::byte{0x33})
        throw std::runtime_error("record copy staging changed under overlap");
}
