#include "mco/entity_flag.hpp"
#include "mco/detail/entity_table.hpp"
#include <cstdint>
#include <stdexcept>

namespace mco {

// Whole body at 0x405df0: read the flag byte of the record at
// table_base[index*28 + 0x1a] and return its low bit as 0 or 1. The original
// reads the base from global 0x8e3ab8; here the table bytes are explicit.
std::uint32_t entity_flag(const std::span<const std::byte> table,
                          std::uint32_t index) {
    const auto offset = detail::entity_offset(table, index, entity_record::flags, 1);
    const unsigned byte = std::to_integer<unsigned>(table[static_cast<size_t>(offset)]);
    return byte & 1;
}
}  // namespace mco