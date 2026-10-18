#include "mco/registry_slot_used.hpp"
#include <array>
#include <span>
#include <stdexcept>
int main() {
    std::array<std::byte, 0x1804> registry{};
    mco::registry_slot_used(registry, 3);
    registry[3*24] = std::byte{1};
    if (mco::registry_slot_used(registry, 3) != 1)
        throw std::runtime_error("a nonzero head field must read used");
    registry[3*24] = std::byte{0};
    if (mco::registry_slot_used(registry, 3) != 0)
        throw std::runtime_error("a zero head field must read unused");
    return 0;
}
