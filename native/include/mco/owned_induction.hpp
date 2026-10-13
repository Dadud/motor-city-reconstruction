#pragma once

#include "mco/owned_valuation.hpp"
#include <span>
#include <vector>

namespace mco {
// Original two ordered induction placeholder rules, isolated from the rest
// of component finalization. Removal swaps in the entire last slot, then pops.
std::vector<OwnedPartSlot> prune_owned_induction_placeholders(std::span<const OwnedPartSlot> slots);
} // namespace mco
