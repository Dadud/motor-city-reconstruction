#include "mco/viv.hpp"

#include <algorithm>
#include <array>
#include <limits>
#include <stdexcept>
#include <unordered_set>
#include <utility>

namespace mco {
namespace {
std::uint32_t read_be(std::span<const std::uint8_t> bytes, std::size_t offset) {
    return (static_cast<std::uint32_t>(bytes[offset]) << 24)
         | (static_cast<std::uint32_t>(bytes[offset + 1]) << 16)
         | (static_cast<std::uint32_t>(bytes[offset + 2]) << 8)
         | static_cast<std::uint32_t>(bytes[offset + 3]);
}
std::string latin1_utf8(std::span<const std::uint8_t> bytes) {
    std::string result;
    for (auto value : bytes) {
        if (value < 128) result.push_back(static_cast<char>(value));
        else {
            result.push_back(static_cast<char>(0xc0u | (value >> 6)));
            result.push_back(static_cast<char>(0x80u | (value & 0x3fu)));
        }
    }
    return result;
}
} // namespace

std::vector<VivEntry> parse_viv_directory(std::span<const std::uint8_t> archive) {
    if (archive.size() < 16) throw std::invalid_argument("truncated VIV header");
    const std::array<std::uint8_t, 4> bigf{'B', 'I', 'G', 'F'};
    const std::array<std::uint8_t, 4> big4{'B', 'I', 'G', '4'};
    if (!std::equal(bigf.begin(), bigf.end(), archive.begin()) &&
        !std::equal(big4.begin(), big4.end(), archive.begin()))
        throw std::invalid_argument("unsupported VIV signature");
    const auto size = read_be(archive, 4);
    const auto count = read_be(archive, 8);
    const auto end = read_be(archive, 12);
    if (size != archive.size() || end < 16 || end > archive.size())
        throw std::invalid_argument("invalid VIV archive or directory size");
    if (count > (end - 16) / 9)
        throw std::invalid_argument("invalid VIV entry count");
    std::size_t cursor = 16;
    std::vector<VivEntry> entries;
    std::unordered_set<std::string> names;
    std::vector<std::pair<std::uint64_t, std::uint64_t>> ranges;
    for (std::uint32_t i = 0; i < count; ++i) {
        if (end - cursor < 8) throw std::invalid_argument("truncated VIV entry");
        const auto offset = read_be(archive, cursor);
        const auto length = read_be(archive, cursor + 4);
        cursor += 8;
        const auto name_start = cursor;
        while (cursor < end && archive[cursor] != 0) ++cursor;
        if (cursor == end) throw std::invalid_argument("unterminated VIV name");
        auto name = latin1_utf8(archive.subspan(name_start, cursor - name_start));
        ++cursor;
        if (name.empty() || !names.insert(name).second)
            throw std::invalid_argument("empty or duplicate VIV name");
        const auto payload_end = static_cast<std::uint64_t>(offset) + length;
        if (offset < end || payload_end > archive.size())
            throw std::invalid_argument("invalid VIV payload bounds");
        if (length != 0) ranges.emplace_back(offset, payload_end);
        entries.push_back({std::move(name), offset, length});
    }
    std::sort(ranges.begin(), ranges.end());
    for (std::size_t i = 1; i < ranges.size(); ++i)
        if (ranges[i].first < ranges[i - 1].second)
            throw std::invalid_argument("overlapping VIV payloads");
    return entries;
}
} // namespace mco
