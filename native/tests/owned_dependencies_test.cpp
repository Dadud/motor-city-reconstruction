#include "mco/owned_dependencies.hpp"

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
std::int32_t integer(const mco::OwnedPartSlot& slot, std::size_t offset) {
    std::uint32_t bits = 0;
    for (std::size_t i = 0; i < 4; ++i) bits |= static_cast<std::uint32_t>(slot[offset + i]) << (8 * i);
    return std::bit_cast<std::int32_t>(bits);
}
mco::OwnedPartSlot slot(std::int32_t abstract = 101, std::int32_t attachment = 10,
                        std::int32_t parent = 0, std::int32_t dependency = 77,
                        std::int32_t flag = 91, std::int32_t owned_id = 1) {
    mco::OwnedPartSlot value;
    value.fill(0xa5);
    put(value, 0, abstract); put(value, 0x600, parent); put(value, 0x604, dependency);
    put(value, 0x61c, attachment); put(value, 0x634, flag); put(value, 0x5f8, owned_id);
    return value;
}
void reject(std::span<const mco::OwnedPartSlot> slots, std::span<const std::int32_t> ids) {
    bool rejected = false;
    try { mco::link_owned_dependencies(slots, ids); }
    catch (const std::invalid_argument&) { rejected = true; }
    check(rejected, "malformed dependency input accepted");
}
} // namespace

int main() {
    std::vector<mco::OwnedPartSlot> source{slot(), slot(500, 10), slot(500, 99), slot(500, 0)};
    std::vector<std::int32_t> ids{500, 0, 0, 0};
    auto result = mco::link_owned_dependencies(source, ids);
    check(integer(result[0], 0x604) == 3 && integer(result[0], 0x634) == 91,
          "last wildcard match or flag preservation mismatch");
    source.pop_back(); ids.pop_back();
    result = mco::link_owned_dependencies(source, ids);
    check(integer(result[0], 0x604) == 1, "mismatched attachment superseded earlier match");
    source = {slot(101, 10, 0, -123), slot(500, 99, 0, 99)}; ids = {500, 0};
    result = mco::link_owned_dependencies(source, ids);
    check(integer(result[0], 0x604) == -123 && integer(result[1], 0x604) == 0,
          "missing match preservation or zero dependency mismatch");
    source = {slot(-1, -10), slot(-1, -10)}; ids = {-1, -1};
    result = mco::link_owned_dependencies(source, ids);
    check(integer(result[0], 0x604) == 1 && integer(result[1], 0x604) == 1,
          "signed ID or self-match mismatch");
    source = {slot(), slot(2001), slot(20001), slot(6001), slot(44, 10, 3), slot(45)};
    ids.assign(source.size(), 0);
    const auto original = source;
    result = mco::link_owned_dependencies(source, ids);
    const std::array<std::int32_t, 6> flags{91, 0, 0, 0, 0, 91};
    for (std::size_t i = 0; i < source.size(); ++i) {
        check(integer(result[i], 0x634) == flags[i], "flag clear rule mismatch");
        for (std::size_t offset = 0; offset < source[i].size(); ++offset)
            if (!(offset >= 0x604 && offset < 0x608) && !(offset >= 0x634 && offset < 0x638))
                check(result[i][offset] == source[i][offset], "unrelated byte changed");
    }
    check(source == original, "input modified");
    put(source[0], 0x5f8, 0);
    result = mco::link_owned_dependencies(source, ids);
    for (const auto& value : result) check(integer(value, 0x634) == 0, "absent root flag not cleared");
    reject({}, {});
    reject(source, std::span<const std::int32_t>{ids}.first(1));
    put(source.back(), 0x600, -1); reject(source, ids);
    put(source.back(), 0x600, static_cast<std::int32_t>(source.size())); reject(source, ids);
    put(source.back(), 0x600, 0); put(source[0], 0x600, -1); reject(source, ids);
}
