#include "mco/entity_flag3.hpp"
#include <array>
#include <span>
#include <stdexcept>

int main() {
    std::array<std::byte, 28*2> table{};
    if (mco::entity_flag3(std::span<const std::byte>{}, 0) != 1)
        throw std::runtime_error("an empty table must return one");
    table[0x1a] = static_cast<std::byte>(0x08);
    if (mco::entity_flag3(table, 0) != 0)
        throw std::runtime_error("bit 3 set must return zero");
    table[0x1a] = static_cast<std::byte>(0x00);
    if (mco::entity_flag3(table, 0) != 1)
        throw std::runtime_error("bit 3 clear must return one");
    table[28 + 0x1a] = static_cast<std::byte>(0x08);
    if (mco::entity_flag3(table, 1) != 0)
        throw std::runtime_error("second record must use its own byte");
    table[28 + 0x1a] = static_cast<std::byte>(0xf7);
    if (mco::entity_flag3(table, 1) != 1)
        throw std::runtime_error("other bits must not leak into the result");
    try {
        mco::entity_flag3(table, 9);
    } catch (const std::invalid_argument&) {
        return 0;
    }
    throw std::runtime_error("index past the table must be rejected");
}
