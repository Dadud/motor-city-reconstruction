#include "mco/owned_aggregates.hpp"

#include <algorithm>
#include <array>
#include <bit>
#include <stdexcept>

namespace mco {
namespace {
std::uint32_t read(const OwnedPartSlot& slot, std::size_t offset) {
    std::uint32_t bits = 0;
    for (std::size_t i = 0; i < 4; ++i) bits |= static_cast<std::uint32_t>(slot[offset + i]) << (8 * i);
    return bits;
}
void write(OwnedPartSlot& slot, std::size_t offset, std::uint32_t bits) {
    for (std::size_t i = 0; i < 4; ++i) slot[offset + i] = static_cast<std::uint8_t>(bits >> (8 * i));
}
bool special(const OwnedPartSlot& slot) {
    constexpr std::array<std::uint32_t, 12> ids{101,1001,2001,3001,36001,210001,37001,4001,38001,15001,5001,6001};
    return std::find(ids.begin(), ids.end(), read(slot, 0)) != ids.end();
}
void validate(std::span<const OwnedPartSlot> slots) {
    if (slots.size() > 10000) throw std::invalid_argument("owned aggregation count exceeds 10000");
}
using Children = std::vector<std::vector<std::size_t>>;
Children children(std::span<const OwnedPartSlot> slots) {
    Children result(slots.size());
    for (std::size_t i = 0; i < slots.size(); ++i) {
        const auto parent = std::bit_cast<std::int32_t>(read(slots[i], 0x600));
        if (parent >= 0 && static_cast<std::size_t>(parent) < slots.size() && static_cast<std::size_t>(parent) != i)
            result[static_cast<std::size_t>(parent)].push_back(i);
    }
    return result;
}
struct CountFrame { std::size_t index, cursor; std::uint32_t total; };
std::uint32_t count(std::size_t root, std::span<const OwnedPartSlot> slots, const Children& edges) {
    auto initial = [&](std::size_t index) -> std::uint32_t {
        return read(slots[index], 0x1e3) != 0 && read(slots[index], 0xc) == 0 ? 1 : 0;
    };
    std::vector<bool> active(slots.size());
    std::vector<CountFrame> stack{{root, 0, initial(root)}};
    active[root] = true;
    while (!stack.empty()) {
        auto& frame = stack.back();
        bool descended = false;
        while (frame.cursor < edges[frame.index].size()) {
            const auto child = edges[frame.index][frame.cursor++];
            if (read(slots[child], 0x1e3) == 0) continue;
            if (active[child]) throw std::invalid_argument("cyclic owned component count traversal");
            active[child] = true;
            stack.push_back({child, 0, initial(child)});
            descended = true;
            break;
        }
        if (descended) continue;
        const auto total = frame.total;
        active[frame.index] = false;
        stack.pop_back();
        if (stack.empty()) return total;
        stack.back().total += total;
    }
    return 0;
}
struct CostFrame { std::size_t index, cursor; };
void aggregate(std::size_t root, std::vector<OwnedPartSlot>& slots, const Children& edges) {
    std::vector<bool> active(slots.size());
    std::vector<CostFrame> stack{{root, 0}};
    active[root] = true;
    auto add = [&](std::size_t parent, std::size_t child) {
        for (auto offset : {0x62c, 0x630})
            write(slots[parent], offset, read(slots[parent], offset) + read(slots[child], offset));
    };
    while (!stack.empty()) {
        auto& frame = stack.back();
        if (frame.cursor < edges[frame.index].size()) {
            const auto child = edges[frame.index][frame.cursor++];
            if (special(slots[child])) {
                if (active[child]) throw std::invalid_argument("cyclic owned repair/scrap traversal");
                active[child] = true;
                stack.push_back({child, 0});
            } else add(frame.index, child);
        } else {
            const auto child = frame.index;
            active[child] = false;
            stack.pop_back();
            if (!stack.empty()) add(stack.back().index, child);
        }
    }
}
} // namespace

std::vector<OwnedPartSlot> apply_owned_component_counts(std::span<const OwnedPartSlot> slots) {
    validate(slots);
    auto edges = children(slots);
    std::vector<OwnedPartSlot> result(slots.begin(), slots.end());
    for (std::size_t i = 0; i < slots.size(); ++i) write(result[i], 0x638, count(i, slots, edges));
    return result;
}
std::vector<OwnedPartSlot> apply_owned_repair_scrap_aggregates(std::span<const OwnedPartSlot> slots) {
    validate(slots);
    auto edges = children(slots);
    std::vector<OwnedPartSlot> result(slots.begin(), slots.end());
    for (std::size_t i = 0; i < result.size(); ++i)
        if (read(result[i], 0x60c) == 0 && special(result[i])) aggregate(i, result, edges);
    return result;
}
std::vector<OwnedPartSlot> apply_owned_total_price(std::span<const OwnedPartSlot> slots) {
    validate(slots);
    std::vector<OwnedPartSlot> result(slots.begin(), slots.end());
    if (!result.empty()) {
        std::uint32_t total = 0;
        for (const auto& slot : slots) total += read(slot, 0x1eb);
        // Unsigned sum is exactly representable in float64. Original rounding
        // and __ftol low32 reproduce these same bits without a signed cast.
        write(result[0], 0x1eb, total);
    }
    return result;
}
} // namespace mco
