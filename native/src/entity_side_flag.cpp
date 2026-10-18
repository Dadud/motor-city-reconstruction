#include "mco/entity_side_flag.hpp"
#include <bit>
#include <stdexcept>
#include "mco/detail/entity_table.hpp"

namespace mco {
std::uint32_t entity_side_flag(std::span<const std::byte> table, std::uint32_t index,
                              std::uint32_t side) {
    if (table.empty()) return 0;
    const auto offset = detail::entity_offset(table, index, entity_record::flags, 1);
    const auto mask = side != 0 ? 0x20u : 0x10u;
    return (std::to_integer<unsigned>(table[offset]) & mask) != 0 ? 1u : 0u;
}
}
