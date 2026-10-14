#include "mco/owned_postload.hpp"

#include "mco/owned_aggregates.hpp"
#include "mco/owned_dependencies.hpp"
#include "mco/owned_induction.hpp"
#include "mco/owned_insertion.hpp"
#include "mco/owned_ordering.hpp"
#include "mco/owned_parent_links.hpp"

#include <bit>
#include <stdexcept>
#include <unordered_map>

namespace mco {
namespace {
std::int32_t integer(const OwnedPartSlot& slot, std::size_t offset = 0) {
    std::uint32_t bits = 0;
    for (std::size_t i = 0; i < 4; ++i) bits |= static_cast<std::uint32_t>(slot[offset + i]) << (8 * i);
    return std::bit_cast<std::int32_t>(bits);
}
void set_flag(OwnedPartSlot& slot) {
    slot[0x634] = 1;
    slot[0x635] = slot[0x636] = slot[0x637] = 0;
}
std::vector<std::int32_t> dependencies(std::span<const OwnedPartSlot> slots,
                                     std::span<const OwnedPartSlot> cache) {
    std::unordered_map<std::int32_t, std::size_t> lookup;
    for (std::size_t i = 1; i < cache.size(); ++i) lookup.try_emplace(integer(cache[i]), i);
    std::vector<std::int32_t> result;
    result.reserve(slots.size());
    for (const auto& slot : slots) {
        if (integer(slot) == 0)
            throw std::invalid_argument("abstract-zero dependency helper behavior is unrecovered");
        const auto found = lookup.find(integer(slot));
        if (found == lookup.end()) throw std::invalid_argument("owned dependency type is missing from cache");
        const auto index = integer(cache[found->second], 0x604);
        if (index < 0 || static_cast<std::size_t>(index) >= cache.size())
            throw std::invalid_argument("owned dependency cache index is unresolved");
        result.push_back(integer(cache[static_cast<std::size_t>(index)]));
    }
    return result;
}
} // namespace

std::vector<OwnedPartSlot> postprocess_owned_slots(
    std::span<const OwnedPartSlot> slots, std::span<const OwnedPartSlot> resolved_type_cache,
    const OwnedPostloadOptions& options, const DescriptionPass& description_pass) {
    if (slots.empty() || slots.size() > 10000)
        throw std::invalid_argument("owned post-load processing requires 1..10000 slots");
    if (options.enriched && !description_pass)
        throw std::invalid_argument("unrecovered description pass requires an explicit research callback");
    // Validate the cache without changing owned order or dereferencing owned indexes.
    order_owned_candidates({}, resolved_type_cache);
    std::vector<OwnedPartSlot> result(slots.begin(), slots.end());
    if (options.finalize_enabled && options.finalize_mode != 1) {
        result = insert_owned_placeholders(result, resolved_type_cache, options.display_mode);
        result = prune_owned_induction_placeholders(result);
    }
    if (result.empty())
        throw std::invalid_argument("finalization removed every owned post-load slot");
    for (auto& slot : result) set_flag(slot);
    if (options.reorder) result = reorder_owned_parts(result, resolved_type_cache);
    if (options.enriched) {
        // Parent/root pass requires a first slot; the installed caller supplies
        // an actual vehicle root. Do not manufacture one if pruning removed all.
        if (result.empty()) throw std::invalid_argument("finalization removed every owned post-load slot");
        result = link_owned_parents(result, resolved_type_cache);
        const auto resolved_ids = dependencies(result, resolved_type_cache);
        result = link_owned_dependencies(result, resolved_ids);
        const auto count = result.size();
        auto described = description_pass(result);
        if (described.size() != count)
            throw std::invalid_argument("description pass must preserve owned slot count");
        result = apply_owned_component_counts(described);
        result = apply_owned_repair_scrap_aggregates(result);
    }
    return apply_owned_total_price(result);
}
} // namespace mco
