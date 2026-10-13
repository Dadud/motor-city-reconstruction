#include "mco/owned_induction.hpp"

#include <stdexcept>

namespace {
void check(bool value, const char* message) {
    if (!value) throw std::runtime_error(message);
}
void put(mco::OwnedPartSlot& slot, std::size_t offset, std::uint32_t value) {
    for (std::size_t i = 0; i < 4; ++i) slot[offset + i] = static_cast<std::uint8_t>(value >> (8 * i));
}
mco::OwnedPartSlot slot(std::uint32_t abstract, std::uint32_t owned_id = 0, std::uint8_t marker = 0) {
    mco::OwnedPartSlot result;
    result.fill(marker);
    put(result, 0, abstract); put(result, 0x5f8, owned_id);
    return result;
}
} // namespace

int main() {
    using Slots = std::vector<mco::OwnedPartSlot>;
    check(mco::prune_owned_induction_placeholders({}).empty(), "empty slots rejected");
    const Slots unrelated{slot(101, 1, 7), slot(160001, 42, 8)};
    check(mco::prune_owned_induction_placeholders(unrelated) == unrelated, "unrelated records changed");
    for (const auto rule : {std::array<std::uint32_t, 3>{340001, 340333, 340666},
                           std::array<std::uint32_t, 3>{350001, 360001, 350666}}) {
        for (const auto state : {0u, 1u, 2u, 3u}) {
            const auto first = slot(rule[0], (state & 1) ? 11 : 0, 1);
            const auto second = slot(rule[1], (state & 2) ? 22 : 0, 2);
            const auto third = slot(rule[2], 0, 3);
            const Slots source{first, second, third};
            const auto result = mco::prune_owned_induction_placeholders(source);
            const Slots expected = state == 0 ? Slots{third} : state == 1 ? Slots{first} :
                                   state == 2 ? Slots{second} : Slots{first, second};
            check(result == expected, "induction ownership branch mismatch");
            check(source == Slots{first, second, third}, "input modified");
        }
    }
    // Only the first matching abstract ID is deleted, even with duplicates.
    const auto first = slot(340001, 0, 1), duplicate = slot(340001, 0, 2);
    const auto second = slot(340333, 0, 3), third = slot(340666, 0, 4);
    check(mco::prune_owned_induction_placeholders(Slots{first, duplicate, second, third}) == Slots{third, duplicate},
          "duplicate removal or whole last-record swap mismatch");
    // Ownership search covers every matching record, not just the first one.
    const auto owned_duplicate = slot(340001, 0xffffffffu, 5);
    check(mco::prune_owned_induction_placeholders(Slots{first, second, third, owned_duplicate}) == Slots{first, owned_duplicate},
          "duplicate ownership search mismatch");
    // Ordered pairs operate on the result of earlier whole-record removals.
    const auto a = slot(340001, 0, 1), b = slot(340333, 0, 2), c = slot(340666, 0, 3);
    const auto d = slot(350001, 0, 4), e = slot(360001, 0, 5), f = slot(350666, 0, 6);
    check(mco::prune_owned_induction_placeholders(Slots{a, b, c, d, e, f}) == Slots{f, c},
          "ordered pair swap/pop result mismatch");
    // The third record does not participate in deciding the ownership branch.
    check(mco::prune_owned_induction_placeholders(Slots{first, second, slot(340666, 99, 7)}) ==
          Slots{slot(340666, 99, 7)}, "third ownership incorrectly changed branch");
}
