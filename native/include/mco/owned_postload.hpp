#pragma once

#include "mco/owned_valuation.hpp"
#include <functional>
#include <span>
#include <vector>

namespace mco {
struct OwnedPostloadOptions {
    bool finalize_enabled = true;
    std::uint32_t finalize_mode = 0;
    std::uint32_t display_mode = 2;
    bool reorder = true;
    bool enriched = true;
};

// Explicit research boundary for the unrecovered description pass, not a mod
// API. Enriched processing requires it; there is no silent identity default.
using DescriptionPass = std::function<std::vector<OwnedPartSlot>(std::span<const OwnedPartSlot>)>;
std::vector<OwnedPartSlot> postprocess_owned_slots(
    std::span<const OwnedPartSlot> slots, std::span<const OwnedPartSlot> resolved_type_cache,
    const OwnedPostloadOptions& options = {}, const DescriptionPass& description_pass = {});
} // namespace mco
