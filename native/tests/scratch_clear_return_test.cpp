#include "mco/scratch_clear_return.hpp"
#include <array>
#include <stdexcept>
int main() {
    std::array<std::byte,4> target{};
    target.fill(static_cast<std::byte>(0xee));
    if (mco::clear_through(target, 0x00abcd00u) != 0x00abcd00u)
        throw std::runtime_error("the primary value must come back");
    for (unsigned k = 0; k < 4; ++k)
        if (target[k] != std::byte{0})
            throw std::runtime_error("the fallback target must clear");
    if (mco::clear_through({}, 0x80000000u) != 0x80000000u)
        throw std::runtime_error("null fallback must still return the primary");
    return 0;
}
