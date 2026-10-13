#include "mco/owned_insertion.hpp"

#include <bit>
#include <stdexcept>
#include <string>

namespace {
void check(bool value, const char* message) { if (!value) throw std::runtime_error(message); }
void put(mco::OwnedPartSlot& slot, std::size_t offset, std::int32_t value) {
    const auto bits = std::bit_cast<std::uint32_t>(value);
    for (std::size_t i = 0; i < 4; ++i) slot[offset + i] = static_cast<std::uint8_t>(bits >> (8 * i));
}
std::int32_t integer(const mco::OwnedPartSlot& slot, std::size_t offset = 0) {
    std::uint32_t bits = 0;
    for (std::size_t i = 0; i < 4; ++i) bits |= static_cast<std::uint32_t>(slot[offset + i]) << (8 * i);
    return std::bit_cast<std::int32_t>(bits);
}
std::string text(const mco::OwnedPartSlot& slot, std::size_t offset) {
    return std::string(reinterpret_cast<const char*>(slot.data() + offset));
}
mco::OwnedPartSlot record(std::int32_t abstract, std::int32_t parent = 0,
                          std::int32_t owned = 0, std::int32_t attachment = 0,
                          std::int32_t part_type = 0, std::string description = "Description",
                          std::string model = "Model") {
    mco::OwnedPartSlot slot{};
    put(slot, 0, abstract); put(slot, 0x600, parent); put(slot, 0x5f8, owned);
    put(slot, 0x61c, attachment); put(slot, 0x1e7, part_type);
    for (const auto& [offset, value] : {std::pair<std::size_t, std::string>{0x2c7, "Brand"},
         {0x307, model}, {0x347, description}, {0x180, "Category"}})
        std::copy(value.begin(), value.end(), slot.begin() + offset);
    return slot;
}
using Records = std::vector<mco::OwnedPartSlot>;
template<class F> void reject(F function) {
    bool rejected = false;
    try { function(); } catch (const std::invalid_argument&) { rejected = true; }
    check(rejected, "invalid insertion input accepted");
}
} // namespace

int main() {
    Records cache{record(0), record(101), record(1001, 1), record(50, 2), record(51, 1)};
    Records source{record(101, -1, 1)};
    const auto original = source;
    auto result = mco::insert_owned_placeholders(source, cache);
    check(result.size() == 4 && integer(result[1]) == 1001 && integer(result[2]) == 51 && integer(result[3]) == 50,
          "growing insertion order mismatch");
    check(integer(result[3], 0x600) == 2 && source == original, "cache parent index or input preservation mismatch");
    check(mco::insert_owned_placeholders({}, cache).empty(), "empty insertion mismatch");
    cache = {record(0), record(70), record(71, 1), record(101), record(72, 3)};
    check(mco::insert_owned_placeholders(Records{record(70)}, cache).size() == 1, "unowned ordinary parent expanded");
    check(mco::insert_owned_placeholders(Records{record(70, 0, 1)}, cache).size() == 2, "owned parent not expanded");
    check(mco::insert_owned_placeholders(Records{record(101)}, cache).size() == 2, "special parent not expanded");
    check(mco::insert_owned_placeholders(Records{record(0, 0, 1)}, cache).size() == 1, "abstract-zero parent expanded");
    check(mco::insert_owned_placeholders(Records{record(999, 0, 1)}, cache).size() == 1, "missing parent invented");
    cache = {record(0), record(101)};
    for (auto id : {100001,110001,10001,12001,11001,13001,14001}) cache.push_back(record(id, 1));
    result = mco::insert_owned_placeholders(Records{record(101)}, cache);
    check(result.size() == 15, "paired attachment count mismatch");
    for (std::size_t i = 1; i < result.size(); ++i)
        check(integer(result[i], 0x61c) == (i % 2 ? 10 : 11), "paired attachment order mismatch");
    cache = {record(0), record(101), record(10001, 1), record(55, 1)};
    result = mco::insert_owned_placeholders(Records{record(101), record(10001, 0, 0, 10), record(55, 0, 0, 9)}, cache);
    check(result.size() == 5 && integer(result[3], 0x61c) == 11 && integer(result[4], 0x61c) == 0,
          "type/attachment exact suppression mismatch");
    cache = {record(0), record(101), record(23001, 1), record(34001, 1), record(35001, 1), record(55, 1)};
    result = mco::insert_owned_placeholders(Records{record(101), record(99, 0, 0, 0, 2001)}, cache);
    check(result.size() == 3 && integer(result[2]) == 55, "type2001 suppression mismatch");
    cache = {record(0), record(101), record(50, 0, 0, 0, 0, "First", "First model"),
             record(50, 1, 0, 0, 0, "Current", "Other model")};
    result = mco::insert_owned_placeholders(Records{record(101)}, cache);
    check(text(result[1], 0x347) == "Current" && text(result[1], 0x307) == "First model" && integer(result[1], 0x600) == 0,
          "first clone/current description mismatch");
    cache = {record(0), record(1001), record(101, 1)};
    result = mco::insert_owned_placeholders(Records{record(1001)}, cache);
    check(text(result[1], 0x207) == "Brand Model", "placeholder used owned vehicle year formatter");
    result = mco::insert_owned_placeholders(Records{record(1001)}, cache, 0);
    check(text(result[1], 0x207) == "Model" && text(result[1], 0x287) == "Model", "special short display mismatch");
    cache = {record(0), record(101), record(55, 1)};
    result = mco::insert_owned_placeholders(Records{record(101)}, cache, 1);
    check(text(result[1], 0x207) == "Brand Model", "ordinary display mode mismatch");
    auto expected = cache[2];
    const std::string name = "Brand Model";
    std::copy(name.begin(), name.end(), expected.begin() + 0x207);
    check(mco::insert_owned_placeholders(Records{record(101)}, cache)[1] == expected, "unrelated clone bytes changed");
    reject([&] { mco::insert_owned_placeholders(Records{record(101)}, cache, 2, 1); });
    reject([&] { mco::insert_owned_placeholders({}, cache, 2, 0); });
    reject([&] { mco::insert_owned_placeholders(source, {}); });
    reject([&] { mco::insert_owned_placeholders(source, Records{record(0), record(1, 1)}); });
    for (auto offset : {0x347, 0x307, 0x2c7, 0x180}) {
        auto corrupt = cache;
        std::fill(corrupt[2].begin() + offset, corrupt[2].begin() + offset + 64, std::uint8_t{'X'});
        reject([&] { mco::insert_owned_placeholders(Records{record(101)}, corrupt); });
    }
}
