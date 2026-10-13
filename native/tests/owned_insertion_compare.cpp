#include "mco/owned_insertion.hpp"

#include <array>
#include <cstdio>
#include <iostream>
#include <stdexcept>
#ifdef _WIN32
#include <fcntl.h>
#include <io.h>
#endif

namespace {
std::uint32_t read_u32() {
    std::array<unsigned char, 4> bytes{};
    if (!std::cin.read(reinterpret_cast<char*>(bytes.data()), bytes.size()))
        throw std::invalid_argument("truncated insertion comparison header");
    std::uint32_t value = 0;
    for (unsigned i = 0; i < 4; ++i) value |= std::uint32_t(bytes[i]) << (8 * i);
    return value;
}
std::vector<mco::OwnedPartSlot> read_slots(std::uint32_t count) {
    if (count > 10000) throw std::invalid_argument("comparison count exceeds 10000");
    std::vector<mco::OwnedPartSlot> records(count);
    for (auto& record : records)
        if (!std::cin.read(reinterpret_cast<char*>(record.data()), record.size()))
            throw std::invalid_argument("truncated insertion comparison records");
    return records;
}
void write_count(std::uint32_t value) {
    for (unsigned i = 0; i < 4; ++i)
        std::cout.put(static_cast<char>((value >> (8 * i)) & 0xffu));
}
} // namespace

int main() {
#ifdef _WIN32
    if (_setmode(_fileno(stdin), _O_BINARY) == -1 ||
        _setmode(_fileno(stdout), _O_BINARY) == -1) return 2;
#endif
    try {
        const auto count = read_u32();
        const auto template_count = read_u32();
        const auto mode = read_u32();
        const auto slots = read_slots(count);
        const auto templates = read_slots(template_count);
        if (std::cin.peek() != std::char_traits<char>::eof())
            throw std::invalid_argument("unexpected trailing insertion comparison data");
        const auto result = mco::insert_owned_placeholders(slots, templates, mode);
        write_count(static_cast<std::uint32_t>(result.size()));
        for (const auto& record : result)
            std::cout.write(reinterpret_cast<const char*>(record.data()), record.size());
        return std::cout ? 0 : 2;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
