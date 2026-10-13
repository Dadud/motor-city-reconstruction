#include "mco/owned_parent_links.hpp"

#include <bit>
#include <limits>
#include <optional>
#include <stdexcept>
#include <unordered_map>
#include <unordered_set>
#include <utility>

namespace mco {
namespace {
std::uint32_t read_u32(const OwnedPartSlot& slot, std::size_t offset = 0) {
    std::uint32_t value = 0;
    for (std::size_t i = 0; i < 4; ++i)
        value |= static_cast<std::uint32_t>(slot[offset + i]) << (8 * i);
    return value;
}
std::int32_t read_i32(const OwnedPartSlot& slot, std::size_t offset = 0) {
    return std::bit_cast<std::int32_t>(read_u32(slot, offset));
}
void write_i32(OwnedPartSlot& slot, std::size_t offset, std::int32_t value) {
    const auto bits = std::bit_cast<std::uint32_t>(value);
    for (std::size_t i = 0; i < 4; ++i)
        slot[offset + i] = static_cast<std::uint8_t>(bits >> (8 * i));
}
using Lookup = std::unordered_map<std::int32_t, std::size_t>;

std::size_t distance(std::int32_t abstract, std::int32_t target,
                     std::span<const OwnedPartSlot> templates, const Lookup& lookup) {
    std::size_t steps = 0;
    std::unordered_set<std::int32_t> seen;
    while (abstract != 0 && abstract != target) {
        if (!seen.insert(abstract).second)
            throw std::invalid_argument("cyclic abstract-part parent chain");
        ++steps;
        const auto found = lookup.find(abstract);
        if (found == lookup.end()) return steps;
        const auto parent = static_cast<std::size_t>(read_i32(templates[found->second], 0x600));
        abstract = read_i32(templates[parent]);
    }
    return steps;
}
Lookup validate(std::span<const OwnedPartSlot> slots, std::span<const OwnedPartSlot> templates) {
    if (slots.empty() || templates.empty())
        throw std::invalid_argument("expected nonempty owned slots and resolved type cache");
    constexpr auto index_limit = static_cast<std::size_t>(std::numeric_limits<std::int32_t>::max());
    if (slots.size() > index_limit || templates.size() > index_limit)
        throw std::invalid_argument("owned and type-cache indexes must fit int32");
    if (read_i32(templates[0]) != 0)
        throw std::invalid_argument("type-cache index zero must be abstract-zero sentinel");
    for (const auto& record : templates) {
        const auto parent = read_i32(record, 0x600);
        if (parent < 0 || static_cast<std::size_t>(parent) >= templates.size())
            throw std::invalid_argument("resolved type parent index must reference cache");
    }
    for (const auto& record : slots) {
        const auto parent = read_i32(record, 0x600);
        if (parent < 0 || static_cast<std::size_t>(parent) >= slots.size())
            throw std::invalid_argument("owned parent index must reference existing slot");
    }
    Lookup lookup;
    for (std::size_t i = 1; i < templates.size(); ++i) lookup.try_emplace(read_i32(templates[i]), i);
    for (const auto& entry : lookup) distance(entry.first, 0, templates, lookup);
    return lookup;
}
OwnedRootSelection select(std::span<const OwnedPartSlot> slots,
                          std::span<const OwnedPartSlot> templates, const Lookup& lookup) {
    OwnedRootSelection result{{slots.begin(), slots.end()}, 1};
    if (slots.size() <= 1) return result;
    for (std::size_t i = 0; i < slots.size(); ++i) {
        const auto found = lookup.find(read_i32(slots[i]));
        if (found == lookup.end()) { result.status = 3; return result; }
        const auto parent = static_cast<std::size_t>(read_i32(templates[found->second], 0x600));
        if (read_i32(templates[parent]) == 0) {
            std::swap(result.slots[0], result.slots[i]);
            return result;
        }
    }
    std::size_t best = 0, minimum = 255;
    for (std::size_t i = 0; i < slots.size(); ++i) {
        const auto abstract = read_i32(slots[i]);
        if (abstract == 1001) { best = i; break; }
        const auto steps = distance(abstract, 1001, templates, lookup);
        if (steps < minimum) { best = i; minimum = steps; }
    }
    std::swap(result.slots[0], result.slots[best]);
    return result;
}
} // namespace

OwnedRootSelection select_owned_root(std::span<const OwnedPartSlot> slots,
                                    std::span<const OwnedPartSlot> resolved_type_cache) {
    const auto lookup = validate(slots, resolved_type_cache);
    return select(slots, resolved_type_cache, lookup);
}
std::vector<OwnedPartSlot> link_owned_parents(std::span<const OwnedPartSlot> slots,
                                           std::span<const OwnedPartSlot> resolved_type_cache) {
    const auto lookup = validate(slots, resolved_type_cache);
    // The original parent-link caller ignores root-selection status.
    auto result = select(slots, resolved_type_cache, lookup).slots;
    for (std::size_t parent_index = 0; parent_index < result.size(); ++parent_index) {
        const auto parent_abstract = read_i32(result[parent_index]);
        const auto parent_attachment = read_i32(result[parent_index], 0x61c);
        for (auto& child : result) {
            const auto abstract = read_i32(child);
            const auto found = lookup.find(abstract);
            const auto template_parent = abstract == 0 || found == lookup.end() ? 0
                : read_i32(resolved_type_cache[found->second], 0x600);
            if (template_parent != 0 &&
                read_i32(resolved_type_cache[static_cast<std::size_t>(template_parent)]) == parent_abstract &&
                (parent_attachment == 0 || read_i32(child, 0x61c) == parent_attachment))
                write_i32(child, 0x600, static_cast<std::int32_t>(parent_index));
        }
    }
    std::optional<std::size_t> target, source;
    for (std::size_t i = 0; i < result.size(); ++i) {
        if (read_i32(result[i]) == 36001) target = i;
        if (read_i32(result[i]) == 160001 && read_u32(result[i], 0x1e3) != 0) source = i;
    }
    if (target) {
        if (source) write_i32(result[*target], 0x203, read_i32(result[*source], 0x203));
        else {
            write_i32(result[*target], 0x203, 0);
            for (const auto& child : result) {
                const auto found = lookup.find(read_i32(child));
                if (read_i32(child, 0x600) == static_cast<std::int32_t>(*target) &&
                    read_i32(child, 0x203) != 0 && found != lookup.end() &&
                    read_i32(resolved_type_cache[found->second], 0x14) != 0)
                    write_i32(result[*target], 0x203, read_i32(child, 0x203));
            }
        }
    }
    return result;
}
} // namespace mco
