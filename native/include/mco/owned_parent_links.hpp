#pragma once

#include "mco/owned_valuation.hpp"
#include <span>
#include <vector>

namespace mco {
struct OwnedRootSelection {
    std::vector<OwnedPartSlot> slots;
    std::int32_t status;
};

// Type-cache records use the original 1596-byte layout and resolved parent
// indexes; cache index zero must be the abstract-zero sentinel.
OwnedRootSelection select_owned_root(std::span<const OwnedPartSlot> slots,
                                    std::span<const OwnedPartSlot> resolved_type_cache);
// Original root selection, parent links and EngineBlockFamilyID propagation.
// This isolated pass neither loads type templates nor completes an assembly.
std::vector<OwnedPartSlot> link_owned_parents(std::span<const OwnedPartSlot> slots,
                                           std::span<const OwnedPartSlot> resolved_type_cache);
} // namespace mco
