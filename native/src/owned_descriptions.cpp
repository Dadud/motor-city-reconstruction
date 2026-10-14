#include "mco/owned_descriptions.hpp"
#include <algorithm>
#include <array>
#include <bit>
#include <stdexcept>
#include <unordered_map>

namespace mco {
namespace {
std::int32_t integer(const OwnedPartSlot& slot, std::size_t offset = 0) {
    std::uint32_t value = 0;
    for (unsigned i = 0; i < 4; ++i) value |= std::uint32_t(slot[offset + i]) << (8 * i);
    return std::bit_cast<std::int32_t>(value);
}
std::string text(const OwnedPartSlot& slot, std::size_t offset, std::size_t capacity) {
    const auto first = slot.begin() + offset;
    const auto last = std::find(first, first + capacity, std::uint8_t{0});
    if (last == first + capacity) throw std::invalid_argument("description text lacks bounded terminator");
    return {first, last};
}
bool special(std::int32_t abstract) {
    constexpr std::array<std::int32_t, 12> ids{101,1001,2001,3001,36001,210001,37001,4001,38001,15001,5001,6001};
    return std::find(ids.begin(), ids.end(), abstract) != ids.end();
}
}
std::vector<OwnedPartSlot> apply_owned_descriptions(
    std::span<const OwnedPartSlot> slots, std::span<const OwnedPartSlot> templates,
    const AttachmentLabels& labels, const LeafDescription& leaf_description) {
    if (slots.size() > 10000 || templates.empty() || integer(templates[0]) != 0)
        throw std::invalid_argument("expected bounded slots and abstract-zero cache sentinel");
    for (const auto& [key, label] : labels)
        if (key < 1 || key > 11 || label.size() > 128 || label.find('\0') != std::string::npos)
            throw std::invalid_argument("invalid bounded attachment label");
    std::unordered_map<std::int32_t, std::size_t> lookup;
    for (std::size_t i = 1; i < templates.size(); ++i) lookup.try_emplace(integer(templates[i]), i);
    std::vector<OwnedPartSlot> result(slots.begin(), slots.end());
    for (std::size_t index = 0; index < result.size(); ++index) {
        auto& slot = result[index];
        const auto abstract = integer(slot);
        std::string description;
        if (integer(slot, 0x1e3) == 0) {
            const auto found = lookup.find(abstract);
            if (found == lookup.end()) continue;
            description = text(templates[found->second], 0x20, 352);
            if (description.empty()) description = " ";
        } else if (!special(abstract)) {
            if (!leaf_description) throw std::invalid_argument("branded leaf description requires explicit renderer");
            slot = leaf_description(slot);
            continue;
        } else {
            for (std::size_t child_index = 0; child_index < result.size(); ++child_index) {
                const auto& child = result[child_index];
                if (child_index == index || integer(child, 0x1e3) == 0 ||
                    integer(child, 0x600) != static_cast<std::int32_t>(index)) continue;
                const auto attachment = integer(child, 0x61c);
                const auto label = labels.find(attachment);
                if (attachment >= 1 && attachment <= 11 && label == labels.end())
                    throw std::invalid_argument("missing original/localized attachment label");
                const auto line = text(child, 0x287, 64) + " " +
                    (label == labels.end() ? std::string{} : label->second) +
                    (attachment == 0 ? "" : " ") + text(child, 0x180, 64);
                const auto candidate = description + (description.empty() ? "" : "\n") + line;
                if (candidate.size() > 351) break;
                description = candidate;
            }
        }
        std::copy(description.begin(), description.end(), slot.begin() + 0x20);
        slot[0x20 + description.size()] = 0;
    }
    return result;
}
}
