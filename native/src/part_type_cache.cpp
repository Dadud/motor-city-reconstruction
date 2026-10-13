#include "mco/part_type_cache.hpp"

#include <bit>
#include <limits>
#include <stdexcept>
#include <unordered_map>

namespace mco {
namespace {
std::int32_t read_i32(const OwnedPartSlot& record, std::size_t offset) {
    std::uint32_t bits = 0;
    for (std::size_t i = 0; i < 4; ++i)
        bits |= static_cast<std::uint32_t>(record[offset + i]) << (8 * i);
    return std::bit_cast<std::int32_t>(bits);
}
void write_i32(OwnedPartSlot& record, std::size_t offset, std::int32_t value) {
    const auto bits = std::bit_cast<std::uint32_t>(value);
    for (std::size_t i = 0; i < 4; ++i)
        record[offset + i] = static_cast<std::uint8_t>(bits >> (8 * i));
}
} // namespace

std::vector<OwnedPartSlot> resolve_part_type_cache(std::span<const OwnedPartSlot> records) {
    if (records.empty()) throw std::invalid_argument("expected nonempty part-type cache records");
    if (records.size() > static_cast<std::size_t>(std::numeric_limits<std::int32_t>::max()))
        throw std::invalid_argument("part-type cache count must fit int32");
    if (read_i32(records[0], 0) != 0)
        throw std::invalid_argument("part-type cache must begin with abstract-zero sentinel");
    std::unordered_map<std::int32_t, std::int32_t> lookup;
    for (std::size_t i = 1; i < records.size(); ++i)
        lookup.try_emplace(read_i32(records[i], 0), static_cast<std::int32_t>(i));
    std::vector<OwnedPartSlot> result(records.begin(), records.end());
    for (std::size_t i = 1; i < records.size(); ++i) {
        for (const auto offset : {std::size_t{4}, std::size_t{8}}) {
            const auto identifier = read_i32(records[i], offset);
            if (identifier == 0) write_i32(result[i], offset == 4 ? 0x600 : 0x604, 0);
            else {
                const auto found = lookup.find(identifier);
                if (found != lookup.end()) write_i32(result[i], offset == 4 ? 0x600 : 0x604, found->second);
            }
        }
    }
    return result;
}
} // namespace mco
