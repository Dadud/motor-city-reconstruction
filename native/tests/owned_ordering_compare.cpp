#include "mco/owned_ordering.hpp"

#include <array>
#include <cstdio>
#include <iostream>
#include <stdexcept>
#ifdef _WIN32
#include <fcntl.h>
#include <io.h>
#endif

namespace {
std::uint32_t read_count() {
    std::array<unsigned char, 4> bytes{};
    if (!std::cin.read(reinterpret_cast<char*>(bytes.data()), bytes.size()))
        throw std::invalid_argument("truncated ordering comparison header");
    std::uint32_t value = 0;
    for (unsigned i = 0; i < 4; ++i) value |= std::uint32_t(bytes[i]) << (8 * i);
    if (value > 10000) throw std::invalid_argument("ordering comparison count exceeds 10000");
    return value;
}
std::vector<mco::OwnedPartSlot> read_slots(std::uint32_t count) {
    std::vector<mco::OwnedPartSlot> result(count);
    for (auto& slot : result)
        if (!std::cin.read(reinterpret_cast<char*>(slot.data()), slot.size()))
            throw std::invalid_argument("truncated ordering comparison records");
    return result;
}
void write_slots(const std::vector<mco::OwnedPartSlot>& slots) {
    for (const auto& slot : slots)
        std::cout.write(reinterpret_cast<const char*>(slot.data()), slot.size());
}
} // namespace

int main() {
#ifdef _WIN32
    if (_setmode(_fileno(stdin), _O_BINARY) == -1 ||
        _setmode(_fileno(stdout), _O_BINARY) == -1) return 2;
#endif
    try {
        const auto count = read_count();
        const auto cache_count = read_count();
        const auto slots = read_slots(count);
        const auto cache = read_slots(cache_count);
        if (std::cin.peek() != std::char_traits<char>::eof())
            throw std::invalid_argument("unexpected trailing ordering comparison data");
        const auto candidate = mco::order_owned_candidates(slots, cache);
        const auto candidate_count = static_cast<std::uint32_t>(candidate.size());
        for (unsigned i = 0; i < 4; ++i)
            std::cout.put(static_cast<char>((candidate_count >> (8 * i)) & 0xffu));
        write_slots(candidate);
        write_slots(mco::reorder_owned_parts(slots, cache));
        return std::cout ? 0 : 2;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
