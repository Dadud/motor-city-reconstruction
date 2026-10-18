#include "mco/table_byte_read.hpp"
#include <array>
#include <stdexcept>
int main() {
    std::array<std::byte, 64> table{};
    for (std::size_t k = 0; k < table.size(); ++k)
        table[k] = static_cast<std::byte>(k + 1);
    for (std::int32_t index = 0; index < 64; ++index)
        if (mco::table_byte_read(table, index)
                != static_cast<std::uint8_t>(index + 1))
            throw std::runtime_error("flat read regression");
    if (mco::table_byte_read(table, -1) != 0)
        throw std::runtime_error("the -1 index sentinel must return 0");
    try { mco::table_byte_read(table, 64); }
    catch (const std::out_of_range&) { return 0; }
    throw std::runtime_error("an index past the table must be rejected");
}
