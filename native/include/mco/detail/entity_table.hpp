#pragma once
#include "mco/layouts.hpp"
#include <cstdint>
#include <span>
#include <stdexcept>

namespace mco::detail {
inline std::size_t entity_offset(std::span<const std::byte> table,
                                 std::uint32_t index, std::size_t field,
                                 std::size_t width) {
    const auto offset = std::uint64_t(index)*entity_record::size + field;
    if (offset > table.size() || width > table.size()-offset)
        throw std::invalid_argument("entity field outside supplied table");
    return static_cast<std::size_t>(offset);
}

inline std::size_t wrapped_entity_offset(std::span<const std::byte> table,
                                         std::int32_t index, std::int32_t count,
                                         std::size_t field, std::size_t width) {
    if (count <= 0 || std::uint64_t(count)*entity_record::size > table.size())
        throw std::invalid_argument("entity count outside supplied table");
    const auto wrapped = index % count;
    if (wrapped < 0)
        throw std::out_of_range("negative remainder precedes entity table");
    return entity_offset(table, static_cast<std::uint32_t>(wrapped), field, width);
}
}  // namespace mco::detail
