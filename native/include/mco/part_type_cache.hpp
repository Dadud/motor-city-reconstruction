#pragma once

#include "mco/owned_valuation.hpp"
#include <span>
#include <vector>

namespace mco {
// Isolated original cache post-load index resolution. Index-zero sentinel is
// retained verbatim; unresolved nonzero references retain previous indexes.
// Later consumers must validate indexes and cycles before traversing them.
std::vector<OwnedPartSlot> resolve_part_type_cache(std::span<const OwnedPartSlot> records);
} // namespace mco
