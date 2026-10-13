#include "mco/owned_insertion.hpp"

#include <algorithm>
#include <array>
#include <bit>
#include <limits>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <unordered_set>

namespace mco {
namespace {
std::uint32_t read_u32(const OwnedPartSlot& slot, std::size_t offset = 0) {
    std::uint32_t bits = 0;
    for (std::size_t i = 0; i < 4; ++i) bits |= static_cast<std::uint32_t>(slot[offset + i]) << (8 * i);
    return bits;
}
std::int32_t integer(const OwnedPartSlot& slot, std::size_t offset = 0) {
    return std::bit_cast<std::int32_t>(read_u32(slot, offset));
}
void put(OwnedPartSlot& slot, std::size_t offset, std::uint32_t value) {
    for (std::size_t i = 0; i < 4; ++i) slot[offset + i] = static_cast<std::uint8_t>(value >> (8 * i));
}
template<std::size_t N> bool contains(const std::array<std::int32_t, N>& values, std::int32_t value) {
    return std::find(values.begin(), values.end(), value) != values.end();
}
constexpr std::array<std::int32_t, 12> special{101,1001,2001,3001,36001,210001,37001,4001,38001,15001,5001,6001};
constexpr std::array<std::int32_t, 7> paired{100001,110001,10001,12001,11001,13001,14001};
constexpr std::array<std::int32_t, 3> suppressed{23001,34001,35001};
using Lookup = std::unordered_map<std::int32_t, std::size_t>;
Lookup validate(std::span<const OwnedPartSlot> slots, std::span<const OwnedPartSlot> cache,
                std::size_t max_parts) {
    const auto limit = static_cast<std::size_t>(std::numeric_limits<std::int32_t>::max());
    if (!max_parts || slots.size() > max_parts || slots.size() > limit || cache.size() > limit)
        throw std::invalid_argument("owned component count exceeds configured limit");
    if (cache.empty() || integer(cache[0]) != 0)
        throw std::invalid_argument("expected type-cache abstract-zero sentinel");
    for (const auto& entry : cache) {
        const auto parent = integer(entry, 0x600);
        if (parent < 0 || static_cast<std::size_t>(parent) >= cache.size())
            throw std::invalid_argument("resolved type parent index must reference cache");
    }
    Lookup lookup;
    for (std::size_t i = 1; i < cache.size(); ++i) lookup.try_emplace(integer(cache[i]), i);
    for (const auto& entry : lookup) {
        auto abstract = entry.first;
        std::unordered_set<std::int32_t> seen;
        while (abstract != 0) {
            if (!seen.insert(abstract).second) throw std::invalid_argument("cyclic abstract-part parent chain");
            const auto found = lookup.find(abstract);
            if (found == lookup.end()) break;
            abstract = integer(cache[static_cast<std::size_t>(integer(cache[found->second], 0x600))]);
        }
    }
    return lookup;
}
std::string text(const OwnedPartSlot& slot, std::size_t offset, std::size_t capacity) {
    const auto begin = slot.begin() + offset;
    const auto end = std::find(begin, begin + capacity, std::uint8_t{0});
    if (end == begin + capacity) throw std::invalid_argument("placeholder text lacks bounded terminator");
    return std::string(begin, end);
}
void copy_text(OwnedPartSlot& output, std::size_t offset, const std::string& value, std::size_t capacity) {
    if (value.size() >= capacity) throw std::invalid_argument("placeholder text exceeds output region");
    std::copy(value.begin(), value.end(), output.begin() + offset);
    output[offset + value.size()] = 0;
}
OwnedPartSlot clone(const OwnedPartSlot& first, const OwnedPartSlot& current,
                    std::uint32_t attachment, std::uint32_t mode) {
    auto output = first;
    copy_text(output, 0x347, text(current, 0x347, 64), 64);
    put(output, 0x61c, attachment);
    const auto model = text(output, 0x307, 64);
    if (mode != 2) copy_text(output, 0x287, model, 64);
    const auto abstract = integer(output);
    const auto name = mode != 2 && abstract != 0 && contains(special, abstract)
        ? model : text(output, 0x2c7, 64) + " " + model;
    copy_text(output, 0x207, name, 128);
    copy_text(output, 0x180, text(first, 0x180, 64), 64);
    return output;
}
} // namespace

std::vector<OwnedPartSlot> insert_owned_placeholders(
    std::span<const OwnedPartSlot> slots, std::span<const OwnedPartSlot> resolved_type_cache,
    std::uint32_t display_mode, std::size_t max_parts) {
    const auto lookup = validate(slots, resolved_type_cache, max_parts);
    std::vector<OwnedPartSlot> result(slots.begin(), slots.end());
    for (std::size_t cursor = 0; cursor < result.size(); ++cursor) {
        // Copy values before appending: vector reallocation invalidates references.
        const auto abstract = integer(result[cursor]);
        const bool owned = read_u32(result[cursor], 0x5f8) != 0;
        const auto parent = lookup.find(abstract);
        if (abstract == 0 || (!owned && !contains(special, abstract)) || parent == lookup.end()) continue;
        for (std::size_t i = 1; i < resolved_type_cache.size(); ++i) {
            const auto& child = resolved_type_cache[i];
            if (integer(child, 0x600) != static_cast<std::int32_t>(parent->second)) continue;
            const auto child_abstract = integer(child);
            const bool two_attachments = contains(paired, child_abstract);
            for (std::uint32_t attachment = two_attachments ? 10 : 0;
                 attachment <= (two_attachments ? 11u : 0u); ++attachment) {
                if (std::any_of(result.begin(), result.end(), [&](const auto& entry) {
                    return integer(entry) == child_abstract && read_u32(entry, 0x61c) == attachment;
                })) continue;
                if (contains(suppressed, child_abstract) &&
                    std::any_of(result.begin(), result.end(), [](const auto& entry) {
                        return integer(entry, 0x1e7) == 2001;
                    })) continue;
                if (result.size() >= max_parts || result.size() >= static_cast<std::size_t>(std::numeric_limits<std::int32_t>::max()))
                    throw std::invalid_argument("owned component count exceeds configured limit");
                result.push_back(clone(resolved_type_cache[lookup.at(child_abstract)], child, attachment, display_mode));
            }
        }
    }
    return result;
}
} // namespace mco
