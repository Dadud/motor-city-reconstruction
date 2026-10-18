#include "mco/table_byte_read_xy.hpp"
#include <array>
#include <stdexcept>
int main() {
    std::array<std::byte, 300*4> table{};
    for (std::size_t k = 0; k < table.size(); ++k)
        table[k] = static_cast<std::byte>((k*7 + 3) & 0xff);
    for (std::int32_t row = 0; row < 4; ++row)
        for (std::int32_t column = 0; column < 300; ++column) {
            const std::size_t index = static_cast<std::size_t>(row)*300 + column;
            const std::uint8_t want = static_cast<std::uint8_t>((index*7 + 3) & 0xff);
            if (mco::table_byte_read_xy(table, row, column) != want)
                throw std::runtime_error("row/column read regression");
        }
    if (mco::table_byte_read_xy(table, 2, -1) != 0)
        throw std::runtime_error("the -1 column sentinel must return 0");
    try { mco::table_byte_read_xy(table, 4, 0); }
    catch (const std::out_of_range&) { return 0; }
    throw std::runtime_error("a row past the table must be rejected");
}
