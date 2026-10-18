#include "mco/table_byte_read.hpp"
#include <cstddef>
#include <stdexcept>

namespace mco {

// Whole body at 0x42d380: an index of -1 returns 0 without reading the table.
std::uint8_t table_byte_read(const std::span<const std::byte> table,
                             std::int32_t index) {
    if (index == -1)
        return 0;
    if (index < 0 || static_cast<std::uint32_t>(index) >= table.size())
        throw std::out_of_range("table index outside the table");
    return std::to_integer<std::uint8_t>(table[static_cast<std::size_t>(index)]);
}
}  // namespace mco
