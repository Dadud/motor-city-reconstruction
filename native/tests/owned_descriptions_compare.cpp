#include "mco/owned_descriptions.hpp"
#include <algorithm>
#include <array>
#include <cstdio>
#include <iostream>
#include <stdexcept>
#ifdef _WIN32
#include <fcntl.h>
#include <io.h>
#endif

namespace {
std::uint32_t number() {
    std::array<unsigned char, 4> data{};
    if (!std::cin.read(reinterpret_cast<char*>(data.data()), data.size())) throw std::invalid_argument("truncated header");
    std::uint32_t value = 0;
    for (unsigned i = 0; i < 4; ++i) value |= std::uint32_t(data[i]) << (8 * i);
    return value;
}
std::vector<mco::OwnedPartSlot> records(std::uint32_t count) {
    if (count > 10000) throw std::invalid_argument("record count exceeds bound");
    std::vector<mco::OwnedPartSlot> slots(count);
    for (auto& slot : slots)
        if (!std::cin.read(reinterpret_cast<char*>(slot.data()), slot.size())) throw std::invalid_argument("truncated records");
    return slots;
}
}
int main() {
#ifdef _WIN32
    if (_setmode(_fileno(stdin), _O_BINARY) == -1 || _setmode(_fileno(stdout), _O_BINARY) == -1) return 2;
#endif
    try {
        const auto count = number(), cache_count = number();
        const auto slots = records(count), cache = records(cache_count);
        if (std::cin.peek() != std::char_traits<char>::eof()) throw std::invalid_argument("trailing input");
        mco::AttachmentLabels labels;
        for (int i = 1; i <= 11; ++i) labels[i] = "Attachment " + std::to_string(i);
        const auto result = mco::apply_owned_descriptions(slots, cache, labels, [](const auto& source) {
            auto output = source;
            constexpr char fixture[] = "Leaf fixture";
            std::copy(std::begin(fixture), std::end(fixture), output.begin() + 0x20);
            return output;
        });
        for (const auto& slot : result) std::cout.write(reinterpret_cast<const char*>(slot.data()), slot.size());
        return std::cout ? 0 : 2;
    } catch (const std::exception& error) { std::cerr << error.what() << '\n'; return 1; }
}
