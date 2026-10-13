#include "mco/owned_induction.hpp"

#include <array>
#include <utility>

namespace mco {
namespace {
std::uint32_t read_u32(const OwnedPartSlot& slot, std::size_t offset) {
    std::uint32_t value = 0;
    for (std::size_t i = 0; i < 4; ++i)
        value |= static_cast<std::uint32_t>(slot[offset + i]) << (8 * i);
    return value;
}
bool owned(const std::vector<OwnedPartSlot>& slots, std::uint32_t abstract) {
    for (const auto& slot : slots)
        if (read_u32(slot, 0) == abstract && read_u32(slot, 0x5f8) != 0) return true;
    return false;
}
void remove_first(std::vector<OwnedPartSlot>& slots, std::uint32_t abstract) {
    for (std::size_t i = 0; i < slots.size(); ++i)
        if (read_u32(slots[i], 0) == abstract) {
            if (i != slots.size() - 1) std::swap(slots[i], slots.back());
            slots.pop_back();
            return;
        }
}
} // namespace

std::vector<OwnedPartSlot> prune_owned_induction_placeholders(std::span<const OwnedPartSlot> slots) {
    std::vector<OwnedPartSlot> result(slots.begin(), slots.end());
    constexpr std::array<std::array<std::uint32_t, 3>, 2> rules{{
        {340001, 340333, 340666}, {350001, 360001, 350666}}};
    for (const auto& rule : rules) {
        const bool first_owned = owned(result, rule[0]);
        const bool second_owned = owned(result, rule[1]);
        if (!first_owned && !second_owned) {
            remove_first(result, rule[0]);
            remove_first(result, rule[1]);
        } else if (first_owned && !second_owned) {
            remove_first(result, rule[1]);
            remove_first(result, rule[2]);
        } else if (!first_owned && second_owned) {
            remove_first(result, rule[0]);
            remove_first(result, rule[2]);
        } else remove_first(result, rule[2]);
    }
    return result;
}
} // namespace mco
