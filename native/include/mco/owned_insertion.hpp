#pragma once

#include "mco/owned_valuation.hpp"
#include <span>
#include <vector>

namespace mco {
// Recovered dynamic placeholder insertion before parent/dependency linking.
// External cache records retain their original layout. max_parts is an
// authored resource guard, not an original gameplay limit.
std::vector<OwnedPartSlot> insert_owned_placeholders(
    std::span<const OwnedPartSlot> slots,
    std::span<const OwnedPartSlot> resolved_type_cache,
    std::uint32_t display_mode = 2,
    std::size_t max_parts = 10000);
} // namespace mco
