#include "mco/entity_flag.hpp"
#include <array>
#include <stdexcept>

int main() {
    // 28-byte records; byte 0x1a of each record carries the flag.
    std::array<std::byte, 28*3> table{};
    for (unsigned record = 0; record < 3; ++record)
        table[record*28 + 0x1a] = static_cast<std::byte>(record == 1 ? 1 : 0);
    if (mco::entity_flag(table, 0) != 0)
        throw std::runtime_error("clear flag must read as zero");
    if (mco::entity_flag(table, 1) != 1)
        throw std::runtime_error("set flag must read as one");
    if (mco::entity_flag(table, 2) != 0)
        throw std::runtime_error("clear flag must read as zero");
    // Only bit 0 decides: 0x2e has the low bit clear.
    table[0x1a] = static_cast<std::byte>(0x2e);
    if (mco::entity_flag(table, 0) != 0)
        throw std::runtime_error("other bits must not leak into the result");
    table[0x1a] = static_cast<std::byte>(0xff);
    if (mco::entity_flag(table, 0) != 1)
        throw std::runtime_error("0xff must read as one");
    try {
        mco::entity_flag(table, 8);
    } catch (const std::invalid_argument&) {
        return 0;
    }
    throw std::runtime_error("index past the table must be rejected");
}