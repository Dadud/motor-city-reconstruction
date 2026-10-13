#include "mco/part_type_cache.hpp"

#include <bit>
#include <stdexcept>

namespace {
void check(bool value, const char* message) {
    if (!value) throw std::runtime_error(message);
}
void put(mco::OwnedPartSlot& record, std::size_t offset, std::int32_t value) {
    const auto bits = std::bit_cast<std::uint32_t>(value);
    for (std::size_t i = 0; i < 4; ++i) record[offset + i] = static_cast<std::uint8_t>(bits >> (8 * i));
}
std::int32_t integer(const mco::OwnedPartSlot& record, std::size_t offset) {
    std::uint32_t bits = 0;
    for (std::size_t i = 0; i < 4; ++i) bits |= static_cast<std::uint32_t>(record[offset + i]) << (8 * i);
    return std::bit_cast<std::int32_t>(bits);
}
mco::OwnedPartSlot record(std::int32_t abstract, std::int32_t parent = 0,
                          std::int32_t dependency = 0, std::int32_t parent_index = -1,
                          std::int32_t dependency_index = -1) {
    mco::OwnedPartSlot result;
    result.fill(0x5a);
    put(result, 0, abstract); put(result, 4, parent); put(result, 8, dependency);
    put(result, 0x600, parent_index); put(result, 0x604, dependency_index);
    return result;
}
void reject(const std::vector<mco::OwnedPartSlot>& records) {
    bool rejected = false;
    try { mco::resolve_part_type_cache(records); }
    catch (const std::invalid_argument&) { rejected = true; }
    check(rejected, "invalid part-type cache accepted");
}
} // namespace

int main() {
    std::vector<mco::OwnedPartSlot> records{
        record(0, 42, 43, -19, -20), record(10, 20, -3), record(20), record(20),
        record(-3, 0, 0), record(30, 999, 998, -1, 777), record(0, 20, -3)};
    const auto original = records;
    const auto result = mco::resolve_part_type_cache(records);
    check(result[0] == records[0], "sentinel was changed");
    check(integer(result[1], 0x600) == 2 && integer(result[1], 0x604) == 4,
          "first duplicate or signed reference resolution mismatch");
    check(integer(result[2], 0x600) == 0 && integer(result[2], 0x604) == 0 &&
          integer(result[4], 0x600) == 0 && integer(result[4], 0x604) == 0,
          "zero reference resolution mismatch");
    check(integer(result[5], 0x600) == -1 && integer(result[5], 0x604) == 777,
          "missing nonzero references did not preserve previous indexes");
    check(integer(result[6], 0x600) == 2 && integer(result[6], 0x604) == 4,
          "additional abstract-zero data record was skipped");
    check(records == original, "input cache modified");
    for (std::size_t i = 1; i < records.size(); ++i)
        for (std::size_t offset = 0; offset < records[i].size(); ++offset)
            if (offset < 0x600 || offset >= 0x608)
                check(result[i][offset] == records[i][offset], "unrelated cache byte modified");
    check(mco::resolve_part_type_cache(std::vector<mco::OwnedPartSlot>{records[0]})[0] == records[0],
          "sentinel-only cache mismatch");
    // Cyclic relationships are retained by this pass, for later consumers to reject.
    const auto cyclic = mco::resolve_part_type_cache(std::vector<mco::OwnedPartSlot>{record(0), record(10, 20), record(20, 10)});
    check(integer(cyclic[1], 0x600) == 2 && integer(cyclic[2], 0x600) == 1,
          "resolver rejected or rewrote cyclic references");
    reject({});
    reject({record(10)});
}
