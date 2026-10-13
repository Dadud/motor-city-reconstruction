#include "mco/part_type_cache.hpp"
#include <array>
#include <cstdio>
#include <iostream>
#include <stdexcept>
#ifdef _WIN32
#include <fcntl.h>
#include <io.h>
#endif

int main() {
#ifdef _WIN32
    if (_setmode(_fileno(stdin), _O_BINARY) == -1 ||
        _setmode(_fileno(stdout), _O_BINARY) == -1) return 2;
#endif
    try {
        std::array<std::uint8_t, 4> header{};
        if (!std::cin.read(reinterpret_cast<char*>(header.data()), header.size()))
            throw std::invalid_argument("truncated cache count");
        std::uint32_t count = 0;
        for (unsigned i = 0; i < 4; ++i) count |= std::uint32_t(header[i]) << (8 * i);
        if (!count || count > 10000) throw std::invalid_argument("cache count outside 1..10000");
        std::vector<mco::OwnedPartSlot> records(count);
        for (auto& record : records)
            if (!std::cin.read(reinterpret_cast<char*>(record.data()), record.size()))
                throw std::invalid_argument("truncated cache records");
        if (std::cin.peek() != std::char_traits<char>::eof())
            throw std::invalid_argument("unexpected trailing cache input");
        for (const auto& record : mco::resolve_part_type_cache(records))
            std::cout.write(reinterpret_cast<const char*>(record.data()), record.size());
        return std::cout ? 0 : 2;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
