#pragma once

#include "mco/owned_valuation.hpp"
#include <span>
#include <vector>

namespace mco {
// Original abstract-type depth-first ordering with fixed attachment priority.
// Duplicate type/attachment pairs select the first input slot without consuming
// it. The wrapper accepts a candidate only when its count equals input count.
std::vector<OwnedPartSlot> order_owned_candidates(
    std::span<const OwnedPartSlot> slots, std::span<const OwnedPartSlot> resolved_type_cache,
    std::size_t max_parts = 10000);
std::vector<OwnedPartSlot> reorder_owned_parts(
    std::span<const OwnedPartSlot> slots, std::span<const OwnedPartSlot> resolved_type_cache,
    std::size_t max_parts = 10000);
} // namespace mco
