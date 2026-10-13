#include "mco/owned_aggregates.hpp"

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
        std::array<unsigned char, 4> bytes{};
        if (!std::cin.read(reinterpret_cast<char*>(bytes.data()), bytes.size()))
            throw std::invalid_argument("truncated aggregation comparison header");
        std::uint32_t count = 0;
        for (unsigned i = 0; i < 4; ++i) count |= std::uint32_t(bytes[i]) << (8 * i);
        if (count > 10000) throw std::invalid_argument("aggregation comparison count exceeds 10000");
        std::vector<mco::OwnedPartSlot> slots(count);
        for (auto& record : slots)
            if (!std::cin.read(reinterpret_cast<char*>(record.data()), record.size()))
                throw std::invalid_argument("truncated aggregation comparison record");
        if (std::cin.peek() != std::char_traits<char>::eof())
            throw std::invalid_argument("unexpected trailing aggregation comparison data");
        // Independent outputs share the original input; these are not composed.
        for (const auto& output : {mco::apply_owned_component_counts(slots),
                                   mco::apply_owned_repair_scrap_aggregates(slots),
                                   mco::apply_owned_total_price(slots)})
            for (const auto& record : output)
                std::cout.write(reinterpret_cast<const char*>(record.data()), record.size());
        return std::cout ? 0 : 2;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
