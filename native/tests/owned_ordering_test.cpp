#include "mco/owned_ordering.hpp"

#include <array>
#include <stdexcept>

namespace {
void check(bool value, const char* message) { if (!value) throw std::runtime_error(message); }
void put(mco::OwnedPartSlot& slot, std::size_t offset, std::int32_t value) {
    const auto bits = static_cast<std::uint32_t>(value);
    for (std::size_t i = 0; i < 4; ++i) slot[offset + i] = static_cast<std::uint8_t>(bits >> (8 * i));
}
mco::OwnedPartSlot record(std::int32_t abstract, std::int32_t parent = 0,
                          std::int32_t attachment = 0, std::uint8_t marker = 1) {
    mco::OwnedPartSlot result;
    result.fill(marker);
    put(result, 0, abstract); put(result, 0x600, parent); put(result, 0x61c, attachment);
    return result;
}
using Records = std::vector<mco::OwnedPartSlot>;
template<class F> void reject(F function) {
    bool rejected = false;
    try { function(); } catch (const std::invalid_argument&) { rejected = true; }
    check(rejected, "unsafe ordering input accepted");
}
} // namespace

int main() {
    Records cache{record(0), record(101)}, slots, expected;
    constexpr std::array<int, 12> attachments{10,1,2,5,11,3,4,6,7,8,9,0};
    for (int attachment = 0; attachment < 12; ++attachment)
        slots.push_back(record(101, -1, attachment, static_cast<std::uint8_t>(attachment + 1)));
    for (auto attachment : attachments) expected.push_back(slots[attachment]);
    check(mco::order_owned_candidates(slots, cache) == expected, "attachment ordering or whole-record copies mismatch");
    check(mco::reorder_owned_parts(slots, cache) == expected, "count gate rejected full permutation");
    cache = {record(0), record(101), record(10, 1), record(11, 1), record(12, 2)};
    slots = {record(101), record(11), record(12), record(10)};
    check(mco::order_owned_candidates(slots, cache) == Records{slots[0], slots[3], slots[2], slots[1]},
          "depth-first cache ordering mismatch");
    slots.pop_back();
    check(mco::order_owned_candidates(slots, cache) == Records{slots[0], slots[2], slots[1]},
          "cache-only intermediate was not traversed");
    cache = {record(0), record(101)};
    slots = {record(101, 0, 0, 2), record(101, 0, 0, 3), record(101, 0, 99)};
    check(mco::order_owned_candidates(slots, cache) == Records{slots[0]}, "duplicate input pair was consumed");
    check(mco::reorder_owned_parts(slots, cache) == slots, "partial candidate passed count gate");
    cache = {record(0), record(101), record(10, 1), record(10, 1)};
    slots = {record(101), record(10, 0, 0, 22), record(10, 0, 0, 33)};
    expected = {slots[0], slots[1], slots[1]};
    check(mco::order_owned_candidates(slots, cache) == expected, "repeated type emission mismatch");
    check(mco::reorder_owned_parts(slots, cache) == expected, "count gate imposed unverified uniqueness rule");
    cache = {record(0), record(101), record(10, 1), record(10, 1), record(11, 2), record(12, 3)};
    slots = {record(101), record(10), record(11), record(12)};
    check(mco::order_owned_candidates(slots, cache) == Records{slots[0], slots[1], slots[2], slots[1], slots[2]},
          "first cache index did not control child traversal");
    check(mco::reorder_owned_parts(slots, cache) == slots, "oversized candidate passed count gate");
    cache = {record(0), record(101), record(10, 1)};
    for (auto root : {0, 999}) {
        slots = {record(root, -1), record(10, 999)};
        check(mco::order_owned_candidates(slots, cache) == Records{slots[0]}, "zero or missing type gained children");
    }
    check(mco::order_owned_candidates({}, cache).empty(), "empty candidates mismatch");
    check(mco::reorder_owned_parts({}, cache).empty(), "empty ordering mismatch");
    cache = {record(0)};
    for (int index = 1; index <= 1100; ++index) cache.push_back(record(100 + index, index - 1));
    slots = {record(101), record(1200)};
    check(mco::order_owned_candidates(slots, cache) == slots, "deep iterative traversal mismatch");
    cache = {record(0), record(101), record(10, 1), record(10, 1)};
    slots = {record(101), record(10)};
    const auto before = slots;
    reject([&] { mco::order_owned_candidates(slots, cache, 2); });
    check(slots == before, "input modified on failure");
    reject([&] { mco::order_owned_candidates(slots, cache, 0); });
    reject([&] { mco::order_owned_candidates({}, Records{record(0), record(101, -1)}); });
    reject([&] { mco::order_owned_candidates(slots, Records{record(0), record(101, 1)}); });
    reject([&] { mco::order_owned_candidates({}, {}); });
    // Acyclic first-lookup parent chains can still produce a duplicate-type
    // traversal cycle, which the active DFS guard must reject.
    reject([&] { mco::order_owned_candidates(Records{record(101)},
        Records{record(0), record(101), record(10, 1), record(101, 2)}); });
    // Duplicate DAG visits have no emitted slots, so output limits alone do
    // not bound their work. The independent visit cap must still reject them.
    cache = {record(0), record(101)};
    std::int32_t previous = 1;
    for (int level = 0; level < 17; ++level) {
        const auto first = static_cast<std::int32_t>(cache.size());
        cache.push_back(record(200 + level, previous));
        cache.push_back(record(200 + level, previous));
        previous = first;
    }
    reject([&] { mco::order_owned_candidates(Records{record(101)}, cache); });
}
