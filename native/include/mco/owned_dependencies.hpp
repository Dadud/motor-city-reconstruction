#pragma once

#include "mco/owned_valuation.hpp"
#include <span>
#include <vector>

namespace mco {
// Isolated recovered dependency pass. IDs are resolved explicitly by the
// caller; this does not establish parents, choose a root or load templates.
// Malformed parents are rejected before any writes; inputs are never modified.
std::vector<OwnedPartSlot> link_owned_dependencies(
    std::span<const OwnedPartSlot> slots,
    std::span<const std::int32_t> resolved_dependency_ids);
} // namespace mco
