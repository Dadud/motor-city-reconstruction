#include "mco/entity_byte_assign.hpp"
#include <bit>
#include <stdexcept>
#include "mco/detail/entity_table.hpp"

namespace mco {
void entity_byte_assign(std::span<std::byte> table, std::int32_t index,
                          std::int32_t count, std::uint32_t side, std::uint32_t value) {
    if (table.empty()) return;
    const auto field = side != 0 ? entity_record::side1_byte : entity_record::side0_byte;
    const auto offset = detail::wrapped_entity_offset(table, index, count, field, 1);
    table[offset] = static_cast<std::byte>(value & 255u);
}
}
