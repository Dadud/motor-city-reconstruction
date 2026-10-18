#include "mco/entity_side_flag_assign.hpp"
#include <bit>
#include <stdexcept>
#include "mco/detail/entity_table.hpp"

namespace mco {
void entity_side_flag_assign(std::span<std::byte> table, std::int32_t index,
                          std::int32_t count, std::uint32_t side, std::uint32_t value) {
    if (table.empty()) return;
    const auto offset = detail::wrapped_entity_offset(table, index, count, entity_record::flags, 2);
    const auto mask = side != 0 ? 0x20u : 0x10u;
    const auto before = std::to_integer<unsigned>(table[offset])
        | (std::to_integer<unsigned>(table[offset+1]) << 8);
    const auto after = (value & 255u) != 0 ? before | mask : before & ~mask;
    table[offset] = static_cast<std::byte>(after & 255u);
    table[offset+1] = static_cast<std::byte>(after >> 8);
}
}
