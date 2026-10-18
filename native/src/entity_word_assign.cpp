#include "mco/entity_word_assign.hpp"
#include <bit>
#include <stdexcept>
#include "mco/detail/entity_table.hpp"

namespace mco {
void entity_word_assign(std::span<std::byte> table, std::int32_t index,
                          std::int32_t count, std::uint32_t side, std::uint32_t value) {
    if (table.empty()) return;
    // The original uses FLD/FSTP. NaN payload/exception behavior is not
    // established by the emulator, so it is excluded from this host domain.
    if ((value & 0x7f800000u) == 0x7f800000u && (value & 0x007fffffu) != 0)
        throw std::invalid_argument("entity float NaN behavior unverified");
    const auto field = side != 0 ? entity_record::side1_word : entity_record::side0_word;
    const auto offset = detail::wrapped_entity_offset(table, index, count, field, 4);
    for (unsigned k = 0; k < 4; ++k)
        table[offset+k] = static_cast<std::byte>((value >> (k*8)) & 255u);
}
}
