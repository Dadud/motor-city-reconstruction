#include "mco/owned_induction.hpp"
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
            throw std::invalid_argument("truncated induction count");
        std::uint32_t count = 0;
        for (unsigned i = 0; i < 4; ++i) count |= std::uint32_t(header[i]) << (8 * i);
        if (count > 10000) throw std::invalid_argument("induction count exceeds comparison budget");
        std::vector<mco::OwnedPartSlot> records(count);
        for (auto& record : records)
            if (!std::cin.read(reinterpret_cast<char*>(record.data()), record.size()))
                throw std::invalid_argument("truncated induction records");
        if (std::cin.peek() != std::char_traits<char>::eof())
            throw std::invalid_argument("unexpected trailing induction input");
        const auto result = mco::prune_owned_induction_placeholders(records);
        const auto result_count = static_cast<std::uint32_t>(result.size());
        for (unsigned i = 0; i < 4; ++i) std::cout.put(static_cast<char>(result_count >> (8 * i)));
        for (const auto& record : result)
            std::cout.write(reinterpret_cast<const char*>(record.data()), record.size());
        return std::cout ? 0 : 2;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
