#include "mco/owned_aggregates.hpp"

#include <stdexcept>

namespace {
void check(bool value, const char* message) { if (!value) throw std::runtime_error(message); }
void put(mco::OwnedPartSlot& slot, std::size_t offset, std::uint32_t value) {
    for (std::size_t i = 0; i < 4; ++i) slot[offset + i] = static_cast<std::uint8_t>(value >> (8 * i));
}
std::uint32_t read(const mco::OwnedPartSlot& slot, std::size_t offset) {
    std::uint32_t value = 0;
    for (std::size_t i = 0; i < 4; ++i) value |= static_cast<std::uint32_t>(slot[offset + i]) << (8 * i);
    return value;
}
mco::OwnedPartSlot record(std::uint32_t abstract, std::uint32_t parent = 0,
                          std::uint32_t brand = 1, std::uint32_t field_c = 0,
                          std::uint32_t repair = 0, std::uint32_t scrap = 0,
                          std::uint32_t parent_id = 0, std::uint32_t price = 0) {
    mco::OwnedPartSlot value{};
    put(value, 0, abstract); put(value, 0x600, parent); put(value, 0x1e3, brand);
    put(value, 0xc, field_c); put(value, 0x62c, repair); put(value, 0x630, scrap);
    put(value, 0x60c, parent_id); put(value, 0x1eb, price);
    put(value, 0x638, 999);
    return value;
}
using Records = std::vector<mco::OwnedPartSlot>;
template<class F> void reject(F function) {
    bool rejected = false;
    try { function(); } catch (const std::invalid_argument&) { rejected = true; }
    check(rejected, "unsafe aggregate traversal accepted");
}
} // namespace

int main() {
    check(mco::apply_owned_component_counts({}).empty(), "empty counts mismatch");
    check(mco::apply_owned_repair_scrap_aggregates({}).empty(), "empty costs mismatch");
    check(mco::apply_owned_total_price({}).empty(), "empty price mismatch");
    Records slots{record(101, 0, 1, 1), record(50, 0), record(60, 0, 0), record(70, 2), record(80, 1, 1, 1)};
    auto result = mco::apply_owned_component_counts(slots);
    check(read(result[0], 0x638) == 1 && read(result[1], 0x638) == 1 &&
          read(result[2], 0x638) == 1 && read(result[3], 0x638) == 1 && read(result[4], 0x638) == 0,
          "component self/brand traversal rule mismatch");
    // Unbranded children are not descended into, but their own outer count still runs.
    slots = {record(101, 0, 0), record(50, 0, 0), record(60, 1)};
    result = mco::apply_owned_component_counts(slots);
    check(read(result[0], 0x638) == 0 && read(result[1], 0x638) == 1, "unbranded child traversal mismatch");
    slots = {record(101, 0, 1, 0, 10, 100), record(1001, 0, 1, 0, 20, 200), record(50, 1, 1, 0, 3, 30)};
    const auto original = slots;
    result = mco::apply_owned_repair_scrap_aggregates(slots);
    check(read(result[0], 0x62c) == 33 && read(result[1], 0x62c) == 26 && read(result[2], 0x62c) == 3,
          "repeated recursive/outer accumulation mismatch");
    check(read(result[0], 0x630) == 330 && read(result[1], 0x630) == 260, "scrap aggregation mismatch");
    check(slots == original, "aggregate input mutated");
    for (std::size_t i = 0; i < slots.size(); ++i)
        for (std::size_t offset = 0; offset < slots[i].size(); ++offset)
            if (offset < 0x62c || offset >= 0x634) check(result[i][offset] == slots[i][offset], "unrelated cost bytes changed");
    // A nonzero parent instance excludes an outer call, but not a recursive call.
    slots = {record(101, 0, 1, 0, 10), record(1001, 0, 1, 0, 20, 0, 42), record(50, 1, 1, 0, 3)};
    result = mco::apply_owned_repair_scrap_aggregates(slots);
    check(read(result[0], 0x62c) == 33 && read(result[1], 0x62c) == 23, "parent instance outer/recursive distinction lost");
    slots = {record(101, 0, 1, 0, 0xffffffffu, 0x80000000u), record(50, 0, 1, 0, 2, 0xffffffffu)};
    result = mco::apply_owned_repair_scrap_aggregates(slots);
    check(read(result[0], 0x62c) == 1 && read(result[0], 0x630) == 0x7fffffffu, "mod32 costs mismatch");
    slots = {record(101, 0, 1, 0, 0, 0, 0, 0xffffffffu), record(50, 0, 1, 0, 0, 0, 0, 2)};
    result = mco::apply_owned_total_price(slots);
    check(read(result[0], 0x1eb) == 1 && result[1] == slots[1], "mod32 total price mismatch");
    for (std::size_t offset = 0; offset < slots[0].size(); ++offset)
        if (offset < 0x1eb || offset >= 0x1ef) check(result[0][offset] == slots[0][offset], "unrelated price bytes changed");
    slots = {record(101, 0xffffffffu), record(50, 12345)};
    check(read(mco::apply_owned_component_counts(slots)[0], 0x638) == 1, "unmatched parent count mismatch");
    check(mco::apply_owned_repair_scrap_aggregates(slots) == slots, "unmatched parent rejected or changed");
    const Records cycles{record(101, 1), record(1001, 0)};
    reject([&] { mco::apply_owned_component_counts(cycles); });
    reject([&] { mco::apply_owned_repair_scrap_aggregates(cycles); });
    const Records ignored_cycles{record(50, 1, 0), record(60, 0, 0)};
    check(mco::apply_owned_repair_scrap_aggregates(ignored_cycles) == ignored_cycles, "unreachable cost cycle rejected");
    check(read(mco::apply_owned_component_counts(ignored_cycles)[0], 0x638) == 0, "unbranded cycle traversed");
    Records chain;
    for (std::uint32_t i = 0; i < 1100; ++i) chain.push_back(record(50, i ? i - 1 : 0));
    check(read(mco::apply_owned_component_counts(chain)[0], 0x638) == 1100, "iterative deep traversal mismatch");
    const Records excessive(10001);
    reject([&] { mco::apply_owned_component_counts(excessive); });
    reject([&] { mco::apply_owned_repair_scrap_aggregates(excessive); });
    reject([&] { mco::apply_owned_total_price(excessive); });
}
