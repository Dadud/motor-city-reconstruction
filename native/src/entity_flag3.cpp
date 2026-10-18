#include "mco/entity_flag3.hpp"
#include "mco/detail/entity_table.hpp"
#include <stdexcept>

namespace mco {

// Whole body at 0x403440: an empty table returns 1, and otherwise the result
// is the inverse of bit 3 in the record flag byte at
// table[index*28 + 0x1a]. Sibling of entity_flag, which tests bit 0 with
// normal polarity and no empty-table default.
std::uint32_t entity_flag3(const std::span<const std::byte> table,
                           std::uint32_t index) {
    if (table.empty())
        return 1;
    const auto offset = detail::entity_offset(table, index, entity_record::flags, 1);
    const unsigned byte = std::to_integer<unsigned>(table[static_cast<size_t>(offset)]);
    return (byte >> 3 & 1) == 0 ? 1 : 0;
}
}  // namespace mco
