#include "mco/owned_postload.hpp"
#include <algorithm>
#include <array>
#include <bit>
#include <cstdio>
#include <iostream>
#include <stdexcept>
#include <string>
#ifdef _WIN32
#include <fcntl.h>
#include <io.h>
#endif

namespace {
std::uint32_t number() {
    std::array<unsigned char, 4> bytes{};
    if (!std::cin.read(reinterpret_cast<char*>(bytes.data()), bytes.size()))
        throw std::invalid_argument("truncated postload header");
    std::uint32_t result = 0;
    for (unsigned i = 0; i < 4; ++i) result |= std::uint32_t(bytes[i]) << (8 * i);
    return result;
}
std::vector<mco::OwnedPartSlot> records(std::uint32_t count) {
    if (count > 10000) throw std::invalid_argument("postload count exceeds bound");
    std::vector<mco::OwnedPartSlot> result(count);
    for (auto& record : result)
        if (!std::cin.read(reinterpret_cast<char*>(record.data()), record.size()))
            throw std::invalid_argument("truncated postload records");
    return result;
}
}
int main() {
#ifdef _WIN32
    if (_setmode(_fileno(stdin), _O_BINARY) == -1 || _setmode(_fileno(stdout), _O_BINARY) == -1) return 2;
#endif
    try {
        const auto count = number(), cache_count = number();
        mco::OwnedPostloadOptions options;
        const auto enabled = number();
        options.finalize_mode = number(); options.display_mode = number();
        const auto reorder = number(), enriched = number();
        if (enabled > 1 || reorder > 1 || enriched > 1) throw std::invalid_argument("invalid flags");
        options.finalize_enabled = enabled != 0;
        options.reorder = reorder != 0; options.enriched = enriched != 0;
        const auto slots = records(count), cache = records(cache_count);
        if (std::cin.peek() != std::char_traits<char>::eof()) throw std::invalid_argument("trailing input");
        auto fixture = [](std::span<const mco::OwnedPartSlot> input) {
            std::vector<mco::OwnedPartSlot> output(input.begin(), input.end());
            for (auto& slot : output) {
                std::uint32_t id = 0;
                for (unsigned i = 0; i < 4; ++i) id |= std::uint32_t(slot[i]) << (8 * i);
                const auto text = "Fixture type " + std::to_string(std::bit_cast<std::int32_t>(id));
                std::copy(text.begin(), text.end(), slot.begin() + 0x20);
                slot[0x20 + text.size()] = 0;
            }
            return output;
        };
        const auto output = mco::postprocess_owned_slots(slots, cache, options, fixture);
        for (unsigned i = 0; i < 4; ++i) std::cout.put(static_cast<char>((output.size() >> (8 * i)) & 255));
        for (const auto& slot : output) std::cout.write(reinterpret_cast<const char*>(slot.data()), slot.size());
        return std::cout ? 0 : 2;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n'; return 1;
    }
}
