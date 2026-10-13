#include "mco/owned_parent_links.hpp"
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
        throw std::invalid_argument("truncated comparison header");
    std::uint32_t value = 0;
    for (unsigned i = 0; i < 4; ++i) value |= std::uint32_t(bytes[i]) << (8 * i);
    if (!value || value > 10000) throw std::invalid_argument("comparison count outside 1..10000");
    return value;
}
void write_status(std::int32_t status) {
    for (unsigned i = 0; i < 4; ++i)
        std::cout.put(static_cast<char>(static_cast<std::uint32_t>(status) >> (8 * i)));
}
std::vector<mco::OwnedPartSlot> read_slots(std::uint32_t count) {
    std::vector<mco::OwnedPartSlot> records(count);
    for (auto& record : records)
        if (!std::cin.read(reinterpret_cast<char*>(record.data()), record.size()))
            throw std::invalid_argument("truncated comparison records");
    return records;
}
void write_slots(const std::vector<mco::OwnedPartSlot>& records) {
    for (const auto& record : records)
        std::cout.write(reinterpret_cast<const char*>(record.data()), record.size());
}
}
int main() {
#ifdef _WIN32
    if (_setmode(_fileno(stdin), _O_BINARY) == -1 ||
        _setmode(_fileno(stdout), _O_BINARY) == -1) return 2;
#endif
    try {
        const auto count = read_count();
        const auto template_count = read_count();
        const auto slots = read_slots(count);
        const auto templates = read_slots(template_count);
        if (std::cin.peek() != std::char_traits<char>::eof())
            throw std::invalid_argument("unexpected trailing comparison data");
        const auto root = mco::select_owned_root(slots, templates);
        const auto parents = mco::link_owned_parents(slots, templates);
        write_status(root.status);
        write_slots(root.slots);
        write_slots(parents);
        return std::cout ? 0 : 2;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
