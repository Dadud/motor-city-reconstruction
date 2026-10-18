#include "mco/table_byte_read_xy.hpp"
#include <cstddef>
#include <stdexcept>

namespace mco {

// Whole body at 0x42d350: a column of -1 returns 0 without reading the table,
// otherwise the byte sits at row*300 + column.
std::uint8_t table_byte_read_xy(const std::span<const std::byte> table,
                                std::int32_t row, std::int32_t column) {
    if (column == -1)
        return 0;
    const std::int64_t index =
        static_cast<std::int64_t>(row)*300 + column;
    if (index < 0 || static_cast<std::uint64_t>(index) >= table.size())
        throw std::out_of_range("table coordinate outside the table");
    return std::to_integer<std::uint8_t>(table[static_cast<std::size_t>(index)]);
}
}  // namespace mco
