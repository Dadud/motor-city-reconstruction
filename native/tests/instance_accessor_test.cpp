#include "mco/instance_accessor.hpp"
#include <array>
#include <stdexcept>

int main() {
    using mco::instance_accessor;
    if (instance_accessor(0, 0) != 0)
        throw std::runtime_error("both globals zero must return zero");
    if (instance_accessor(0, 0x1234) != 0x1234)
        throw std::runtime_error("zero primary must fall back");
    if (instance_accessor(0x4321, 0x1234) != 0x4321)
        throw std::runtime_error("nonzero primary must win");
    if (instance_accessor(1, 0x9999) != 1)
        throw std::runtime_error("any nonzero primary must win, not just aligned");
    if (instance_accessor(0x80000000, 0) != 0x80000000)
        throw std::runtime_error("high-bit address must survive unchanged");
    const std::array<std::uint32_t,6> cases{0, 1, 0x1234, 0x4321, 0x80000000, 0xffffffff};
    for (auto primary : cases)
        for (auto fallback : cases) {
            const auto expected = primary != 0 ? primary : fallback;
            if (instance_accessor(primary, fallback) != expected)
                throw std::runtime_error("selection rule regression");
        }
    return 0;
}