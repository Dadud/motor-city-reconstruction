#include "mco/viv.hpp"

#include <stdexcept>
#include <vector>

namespace {
void check(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}
void put(std::vector<std::uint8_t>& bytes, std::size_t at, std::uint32_t value) {
    for (std::size_t i = 0; i < 4; ++i)
        bytes[at + i] = static_cast<std::uint8_t>(value >> (24 - 8 * i));
}
std::vector<std::uint8_t> sample() {
    std::vector<std::uint8_t> bytes(29);
    bytes[0] = 'B'; bytes[1] = 'I'; bytes[2] = 'G'; bytes[3] = 'F';
    put(bytes, 4, 29); put(bytes, 8, 1); put(bytes, 12, 26);
    put(bytes, 16, 26); put(bytes, 20, 3);
    bytes[24] = 'a'; bytes[26] = 'x'; bytes[27] = 'y'; bytes[28] = 'z';
    return bytes;
}
void reject(const std::vector<std::uint8_t>& bytes) {
    bool rejected = false;
    try { mco::parse_viv_directory(bytes); }
    catch (const std::invalid_argument&) { rejected = true; }
    check(rejected, "malformed VIV accepted");
}
} // namespace

int main() {
    auto bytes = sample();
    auto entries = mco::parse_viv_directory(bytes);
    check(entries.size() == 1 && entries[0].name == "a" && entries[0].offset == 26 && entries[0].size == 3,
          "valid BIGF directory mismatch");
    bytes[3] = '4';
    check(mco::parse_viv_directory(bytes).size() == 1, "BIG4 rejected");
    bytes[24] = 0xe9;
    check(mco::parse_viv_directory(bytes)[0].name == "\xc3\xa9", "Latin-1 name decoding mismatch");
    bytes = sample(); bytes.resize(12); reject(bytes);
    bytes = sample(); bytes[0] = 'X'; reject(bytes);
    bytes = sample(); put(bytes, 4, 30); reject(bytes);
    bytes = sample(); put(bytes, 12, 15); reject(bytes);
    bytes = sample(); put(bytes, 12, 30); reject(bytes);
    bytes = sample(); put(bytes, 8, 2); reject(bytes);
    bytes = sample(); put(bytes, 16, 27); reject(bytes);
    bytes = sample(); put(bytes, 16, 25); reject(bytes);
    bytes = sample(); put(bytes, 16, 0xfffffffeu); put(bytes, 20, 3); reject(bytes);
    bytes = sample(); bytes[25] = 'b'; reject(bytes);
    bytes = sample(); bytes[24] = 0; reject(bytes);
    // A little-endian offset must not accidentally decode as a valid payload.
    bytes = sample(); bytes[16] = 26; bytes[19] = 0; reject(bytes);
    // Two entries preserve directory order despite reversed payload ordering.
    bytes = sample(); bytes.resize(39); put(bytes, 4, 39); put(bytes, 8, 2); put(bytes, 12, 36);
    put(bytes, 16, 38); put(bytes, 20, 1);
    put(bytes, 26, 36); put(bytes, 30, 2); bytes[34] = 'b'; bytes[35] = 0;
    entries = mco::parse_viv_directory(bytes);
    check(entries.size() == 2 && entries[0].name == "a" && entries[1].name == "b", "entry order changed");
    auto duplicate = bytes; duplicate[34] = 'a'; reject(duplicate);
    auto overlap = bytes; put(overlap, 26, 37); reject(overlap);
    auto truncated_entry = bytes; bytes[25] = 'c'; bytes[34] = 'd'; bytes[35] = 0;
    reject(bytes);
    // Empty payloads may share another payload's offset, as in the Python reader.
    put(truncated_entry, 26, 38); put(truncated_entry, 30, 0);
    check(mco::parse_viv_directory(truncated_entry)[1].size == 0, "empty payload incorrectly overlaps");
    auto empty = sample(); empty.resize(16); put(empty, 4, 16); put(empty, 8, 0); put(empty, 12, 16);
    check(mco::parse_viv_directory(empty).empty(), "empty archive rejected");
}
