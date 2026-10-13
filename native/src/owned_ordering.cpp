#include "mco/owned_ordering.hpp"

#include <array>
#include <bit>
#include <limits>
#include <stdexcept>
#include <unordered_map>
#include <unordered_set>

namespace mco {
namespace {
std::int32_t integer(const OwnedPartSlot& record, std::size_t offset = 0) {
    std::uint32_t bits = 0;
    for (std::size_t i = 0; i < 4; ++i) bits |= static_cast<std::uint32_t>(record[offset + i]) << (8 * i);
    return std::bit_cast<std::int32_t>(bits);
}
using Lookup = std::unordered_map<std::int32_t, std::size_t>;
Lookup validate(std::span<const OwnedPartSlot> slots, std::span<const OwnedPartSlot> cache, std::size_t maximum) {
    const auto limit = static_cast<std::size_t>(std::numeric_limits<std::int32_t>::max());
    if (!maximum || slots.size() > maximum || slots.size() > limit || cache.size() > limit)
        throw std::invalid_argument("owned ordering count exceeds configured limit");
    if (cache.empty() || integer(cache[0]) != 0)
        throw std::invalid_argument("expected abstract-zero type-cache sentinel");
    for (const auto& record : cache) {
        const auto parent = integer(record, 0x600);
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
struct Frame { std::int32_t abstract; std::size_t child_cursor; bool emitted; };
} // namespace

std::vector<OwnedPartSlot> order_owned_candidates(
    std::span<const OwnedPartSlot> slots, std::span<const OwnedPartSlot> resolved_type_cache,
    std::size_t max_parts) {
    const auto lookup = validate(slots, resolved_type_cache, max_parts);
    std::vector<OwnedPartSlot> result;
    if (slots.empty()) return result;
    constexpr std::array<std::int32_t, 12> attachments{10,1,2,5,11,3,4,6,7,8,9,0};
    std::vector<Frame> stack{{integer(slots[0]), 1, false}};
    std::unordered_set<std::int32_t> active;
    std::size_t visits = 0;
    while (!stack.empty()) {
        auto& frame = stack.back();
        if (!frame.emitted) {
            if (++visits > 100000)
                throw std::invalid_argument("owned ordering traversal exceeds visit limit");
            if (!active.insert(frame.abstract).second)
                throw std::invalid_argument("cyclic owned ordering traversal");
            frame.emitted = true;
            for (const auto attachment : attachments) {
                for (const auto& slot : slots) {
                    if (integer(slot) == frame.abstract && integer(slot, 0x61c) == attachment) {
                        if (result.size() >= max_parts)
                            throw std::invalid_argument("owned ordering candidate exceeds configured limit");
                        result.push_back(slot);
                        break;
                    }
                }
            }
        }
        const auto found = lookup.find(frame.abstract);
        if (frame.abstract == 0 || found == lookup.end()) {
            active.erase(frame.abstract); stack.pop_back(); continue;
        }
        bool descended = false;
        while (frame.child_cursor < resolved_type_cache.size()) {
            const auto child_index = frame.child_cursor++;
            if (integer(resolved_type_cache[child_index], 0x600) == static_cast<std::int32_t>(found->second)) {
                const auto abstract = integer(resolved_type_cache[child_index]);
                if (active.contains(abstract)) throw std::invalid_argument("cyclic owned ordering traversal");
                stack.push_back({abstract, 1, false});
                descended = true;
                break;
            }
        }
        if (!descended) { active.erase(frame.abstract); stack.pop_back(); }
    }
    return result;
}
std::vector<OwnedPartSlot> reorder_owned_parts(
    std::span<const OwnedPartSlot> slots, std::span<const OwnedPartSlot> resolved_type_cache,
    std::size_t max_parts) {
    auto candidate = order_owned_candidates(slots, resolved_type_cache, max_parts);
    if (candidate.size() == slots.size()) return candidate;
    return {slots.begin(), slots.end()};
}
} // namespace mco
