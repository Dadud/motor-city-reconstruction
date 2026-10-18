#include "mco/indexed_masked_bit.hpp"
#include <bit>
#include <stdexcept>
#include "mco/clamped_bit_mask.hpp"
#include "mco/layouts.hpp"

namespace mco {
std::uint32_t indexed_masked_bit(std::span<const std::byte> records,
                                 std::uint32_t record, std::int32_t index) {
    const auto offset = std::uint64_t(record)*mask_record::size + mask_record::bits;
    if (offset > records.size() || 4 > records.size()-offset)
        throw std::invalid_argument("mask record outside supplied table");
    std::uint32_t value = 0;
    for (unsigned k = 0; k < 4; ++k)
        value |= std::to_integer<std::uint32_t>(records[static_cast<std::size_t>(offset)+k]) << (k*8);
    return value & clamped_bit_mask(index);
}
}
