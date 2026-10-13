#include "mco/owned_parent_links.hpp"

#include <bit>
#include <stdexcept>

namespace {
void check(bool value, const char* message) {
    if (!value) throw std::runtime_error(message);
}
void put(mco::OwnedPartSlot& slot, std::size_t offset, std::int32_t value) {
    const auto bits = std::bit_cast<std::uint32_t>(value);
    for (std::size_t i = 0; i < 4; ++i) slot[offset + i] = static_cast<std::uint8_t>(bits >> (8 * i));
}
std::int32_t integer(const mco::OwnedPartSlot& slot, std::size_t offset = 0) {
    std::uint32_t bits = 0;
    for (std::size_t i = 0; i < 4; ++i) bits |= static_cast<std::uint32_t>(slot[offset + i]) << (8 * i);
    return std::bit_cast<std::int32_t>(bits);
}
mco::OwnedPartSlot record(std::int32_t abstract, std::int32_t parent = 0,
                          std::int32_t attachment = 0, std::int32_t family = 0,
                          std::int32_t brand = 0, std::int32_t compatible = 0,
                          std::int32_t marker = 0) {
    mco::OwnedPartSlot result{};
    put(result, 0, abstract); put(result, 0x600, parent); put(result, 0x61c, attachment);
    put(result, 0x203, family); put(result, 0x1e3, brand); put(result, 0x14, compatible);
    put(result, 0x5f8, marker);
    return result;
}
void reject(const std::vector<mco::OwnedPartSlot>& slots, const std::vector<mco::OwnedPartSlot>& types) {
    bool root_rejected = false, parents_rejected = false;
    try { mco::select_owned_root(slots, types); }
    catch (const std::invalid_argument&) { root_rejected = true; }
    try { mco::link_owned_parents(slots, types); }
    catch (const std::invalid_argument&) { parents_rejected = true; }
    check(root_rejected && parents_rejected, "invalid root/parent input accepted");
}
} // namespace

int main() {
    using Records = std::vector<mco::OwnedPartSlot>;
    Records types{record(0), record(10, 2), record(20)};
    Records slots{record(10, 0, 0, 0, 0, 0, 4), record(20, 0, 0, 0, 0, 0, 5),
                  record(20, 0, 0, 0, 0, 0, 6)};
    auto selected = mco::select_owned_root(slots, types);
    check(selected.status == 1 && selected.slots == Records{slots[1], slots[0], slots[2]},
          "first top-level whole-record swap mismatch");
    check(mco::select_owned_root(Records{record(99)}, types).status == 1,
          "single missing type did not return early success");
    slots = {record(99), record(20)};
    selected = mco::select_owned_root(slots, types);
    check(selected.status == 3 && selected.slots == slots, "missing type status or no-swap mismatch");
    types = {record(0), record(10, 3), record(10), record(20)};
    slots = {record(10), record(20)};
    check(integer(mco::select_owned_root(slots, types).slots[0]) == 20,
          "duplicate template did not preserve first match");
    types = {record(0), record(10, 3), record(1001, 3), record(20)};
    slots = {record(10), record(1001)};
    check(integer(mco::select_owned_root(slots, types).slots[0]) == 1001, "chassis fallback mismatch");
    types = {record(0), record(10, 3), record(11, 3), record(20)};
    slots = {record(10), record(11)};
    check(mco::select_owned_root(slots, types).slots == slots, "distance tie did not retain first slot");
    types = {record(0), record(1001)};
    for (std::int32_t steps = 1; steps <= 256; ++steps) types.push_back(record(1001 + steps, steps));
    slots = {record(1257), record(1256)};
    check(mco::select_owned_root(slots, types).slots == slots, "strict 255 distance cap mismatch");
    types = {record(0), record(10, 2), record(20)};
    slots = {record(10, 0, 7, 0, 0, 0, 1), record(20, 0, 7, 0, 0, 0, 2),
             record(20, 0, 99, 0, 0, 0, 3), record(20, 0, 0, 0, 0, 0, 4)};
    const auto original = slots;
    auto result = mco::link_owned_parents(slots, types);
    check(integer(result[1], 0x600) == 3 && integer(result[2], 0x600) == 0,
          "last parent wildcard or unmatched-parent preservation mismatch");
    check(slots == original, "input modified");
    const Records reordered{slots[1], slots[0], slots[2], slots[3]};
    for (std::size_t i = 0; i < result.size(); ++i)
        for (std::size_t offset = 0; offset < result[i].size(); ++offset)
            if (offset < 0x600 || offset >= 0x604)
                check(result[i][offset] == reordered[i][offset], "unrelated bytes changed");
    result = mco::link_owned_parents(Records{record(99, 1), record(10), record(20)}, types);
    check(integer(result[0], 0x600) == 1 && integer(result[1], 0x600) == 2,
          "ignored root status prevented other parent links");
    types = {record(0), record(36001), record(160001)};
    slots = {record(36001, 0, 0, 1), record(160001, 0, 0, 55, 3), record(36001, 0, 0, 2),
             record(160001, 0, 0, 66, 4), record(160001, 0, 0, 77, 0)};
    result = mco::link_owned_parents(slots, types);
    check(integer(result[0], 0x203) == 1 && integer(result[2], 0x203) == 66,
          "last branded source / last target family mismatch");
    types = {record(0), record(36001), record(10, 1, 0, 0, 0, 1), record(11, 1)};
    slots = {record(36001, 0, 0, 99), record(10, 0, 0, 44), record(11, 0, 0, 55), record(10, 0, 0, 66)};
    check(integer(mco::link_owned_parents(slots, types)[0], 0x203) == 66,
          "last compatible child family mismatch");
    check(integer(mco::link_owned_parents(Records{record(36001, 0, 0, 99)}, types)[0], 0x203) == 0,
          "family reset without source mismatch");
    reject({}, Records{record(0)});
    reject(Records{record(1)}, {});
    reject(Records{record(1)}, Records{record(1)});
    reject(Records{record(1)}, Records{record(0), record(1, -1)});
    reject(Records{record(1)}, Records{record(0), record(1, 2)});
    reject(Records{record(1, 1)}, Records{record(0), record(1)});
    reject(Records{record(1)}, Records{record(0), record(1, 1)});
    reject(Records{record(1)}, Records{record(0), record(1, 2), record(2, 1)});
}
