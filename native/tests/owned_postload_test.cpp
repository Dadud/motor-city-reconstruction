#include "mco/owned_postload.hpp"

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
                          std::uint32_t brand = 0, std::uint32_t price = 0,
                          std::uint32_t repair = 0) {
    mco::OwnedPartSlot value{};
    put(value, 0, abstract); put(value, 0x600, parent); put(value, 0x1e3, brand);
    put(value, 0x1eb, price); put(value, 0x62c, repair); put(value, 0x638, 777);
    return value;
}
using Records = std::vector<mco::OwnedPartSlot>;
template<class F> void reject(F function) {
    bool rejected = false;
    try { function(); } catch (const std::invalid_argument&) { rejected = true; }
    check(rejected, "invalid post-load processing accepted");
}
} // namespace

int main() {
    Records cache{record(0), record(101), record(2001, 1), record(50, 2)};
    put(cache[3], 0x604, 1);
    Records slots{record(101, 0, 1, 10, 10), record(2001, 0, 1, 20, 20), record(50, 0, 1, 30, 3)};
    for (auto& slot : slots) put(slot, 0x5f8, 1);
    const auto original = slots;
    bool called = false;
    mco::DescriptionPass description = [&](std::span<const mco::OwnedPartSlot> current) {
        called = true;
        check(current.size() == 3 && read(current[1], 0x600) == 0 && read(current[2], 0x600) == 1,
              "description callback ran before parent linking");
        check(read(current[2], 0x604) == 0, "description callback ran before dependency linking");
        check(read(current[0], 0x634) == 1 && read(current[1], 0x634) == 0,
              "flag initialization or dependency flag rules missing before callback");
        check(read(current[0], 0x638) == 777 && read(current[1], 0x62c) == 20,
              "counts or costs ran before description callback");
        Records output(current.begin(), current.end());
        for (auto& slot : output) put(slot, 0x1eb, read(slot, 0x1eb) + 1);
        put(output[2], 0x62c, 7);
        return output;
    };
    auto result = mco::postprocess_owned_slots(slots, cache, {}, description);
    check(called && slots == original, "callback not invoked or inputs modified");
    check(read(result[0], 0x638) == 3 && read(result[1], 0x638) == 2 && read(result[2], 0x638) == 1,
          "component count stage missing");
    check(read(result[0], 0x62c) == 37 && read(result[1], 0x62c) == 34 && read(result[2], 0x62c) == 7,
          "post-description repeated cost aggregation mismatch");
    check(read(result[0], 0x1eb) == 63, "total price did not run after description");
    reject([&] { mco::postprocess_owned_slots(slots, cache); });
    reject([&] { mco::postprocess_owned_slots(slots, cache, {}, [](auto) { return Records{}; }); });
    mco::OwnedPostloadOptions unenriched;
    unenriched.enriched = false;
    cache = {record(0), record(101), record(340001), record(340333), record(340666)};
    slots = {record(101, 0, 0, 1), record(340001, 0, 0, 2), record(340333, 0, 0, 3), record(340666, 0, 0, 4)};
    result = mco::postprocess_owned_slots(slots, cache, unenriched);
    check(result.size() == 2 && read(result[1], 0) == 340666 && read(result[0], 0x1eb) == 5,
          "enabled finalization did not prune induction placeholders");
    for (const auto& value : result) check(read(value, 0x634) == 1, "unenriched flag initialization missing");
    auto skipped = unenriched;
    skipped.finalize_enabled = false;
    result = mco::postprocess_owned_slots(slots, cache, skipped,
        [](auto) -> Records { throw std::runtime_error("unenriched description callback invoked"); });
    check(result.size() == 4 && read(result[0], 0x1eb) == 10, "disabled finalizer failed to skip pruning");
    skipped.finalize_enabled = true; skipped.finalize_mode = 1;
    check(mco::postprocess_owned_slots(slots, cache, skipped).size() == 4, "finalize mode1 failed to skip pruning");
    cache = {record(0), record(101), record(55, 1)};
    slots = {record(101)};
    skipped.finalize_enabled = false; skipped.finalize_mode = 0;
    check(mco::postprocess_owned_slots(slots, cache, skipped).size() == 1, "disabled finalizer did not skip insertion");
    skipped.finalize_enabled = true; skipped.finalize_mode = 1;
    check(mco::postprocess_owned_slots(slots, cache, skipped).size() == 1, "mode1 did not skip insertion");
    check(mco::postprocess_owned_slots(slots, cache, unenriched).size() == 2, "enabled finalizer did not insert placeholder");
    cache = {record(0), record(101)};
    slots = {record(101, 0, 0, 1), record(101, 0, 0, 2)};
    result = mco::postprocess_owned_slots(slots, cache, unenriched);
    check(result.size() == 2 && read(result[0], 0x1eb) == 3, "ordering count gate or total price mismatch");
    reject([&] { mco::postprocess_owned_slots({}, cache, unenriched); });
    reject([&] { mco::postprocess_owned_slots(slots, {}, unenriched); });
    reject([&] { mco::postprocess_owned_slots(Records{record(0)}, Records{record(0)}, {},
        [](auto current) { return Records(current.begin(), current.end()); }); });
    auto unresolved = cache;
    put(unresolved[1], 0x604, 0xffffffffu);
    reject([&] { mco::postprocess_owned_slots(Records{record(101)}, unresolved, {},
        [](auto current) { return Records(current.begin(), current.end()); }); });
}
