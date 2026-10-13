#pragma once

#include "mco/owned_valuation.hpp"
#include <span>
#include <vector>

namespace mco {
// Isolated original aggregation passes; 0x0c semantics remain unassigned.
// Parent indexes are compared, not dereferenced. Unmatched indexes survive.
// Reachable cycles and counts above 10000 are rejected as authored safeguards.
std::vector<OwnedPartSlot> apply_owned_component_counts(std::span<const OwnedPartSlot> slots);
std::vector<OwnedPartSlot> apply_owned_repair_scrap_aggregates(std::span<const OwnedPartSlot> slots);
std::vector<OwnedPartSlot> apply_owned_total_price(std::span<const OwnedPartSlot> slots);
} // namespace mco
