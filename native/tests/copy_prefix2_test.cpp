#include "mco/copy_prefix2.hpp"
#include <stdexcept>
int main() {
    std::array<std::byte,4> backing{std::byte{0x11},std::byte{0x22},std::byte{0x33},std::byte{0x44}};
    mco::copy_prefix2(std::span<std::byte,3>(backing.data()+1,3),
                      std::span<const std::byte,2>(backing.data(),2));
    if (backing[1] != std::byte{0x11} || backing[2] != std::byte{0x22} || backing[3] != std::byte{0})
        throw std::runtime_error("prefix copy must stage source byte one");
}
