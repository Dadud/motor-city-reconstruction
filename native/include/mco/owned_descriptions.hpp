#pragma once
#include "mco/owned_valuation.hpp"
#include <functional>
#include <map>
#include <span>
#include <string>
#include <vector>

namespace mco {
using AttachmentLabels = std::map<std::int32_t, std::string>;
using LeafDescription = std::function<OwnedPartSlot(const OwnedPartSlot&)>;
// Internal research boundary: original localization and branded leaf rendering
// remain explicit inputs, not invented defaults or public mod interfaces.
std::vector<OwnedPartSlot> apply_owned_descriptions(
    std::span<const OwnedPartSlot> slots, std::span<const OwnedPartSlot> templates,
    const AttachmentLabels& attachment_labels, const LeafDescription& leaf_description = {});
}
