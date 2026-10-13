#include "mco/viv.hpp"

#include <array>
#include <cstdio>
#include <iostream>
#include <stdexcept>
#include <vector>
#ifdef _WIN32
#include <fcntl.h>
#include <io.h>
#endif

int main() {
#ifdef _WIN32
    if (_setmode(_fileno(stdin), _O_BINARY) == -1) return 2;
#endif
    constexpr std::size_t budget = 64 * 1024 * 1024;
    std::vector<std::uint8_t> bytes;
    std::array<char, 16384> chunk{};
    try {
        while (std::cin.read(chunk.data(), chunk.size()) || std::cin.gcount() != 0) {
            const auto count = static_cast<std::size_t>(std::cin.gcount());
            if (count > budget - bytes.size()) throw std::invalid_argument("VIV input exceeds 64 MiB budget");
            bytes.insert(bytes.end(), chunk.data(), chunk.data() + count);
        }
        if (std::cin.bad() || (!std::cin.eof() && std::cin.fail()))
            throw std::runtime_error("VIV input read failed");
        constexpr char hex[] = "0123456789abcdef";
        for (const auto& entry : mco::parse_viv_directory(bytes)) {
            std::cout << entry.offset << ' ' << entry.size << ' ';
            for (const auto character : entry.name) {
                const auto value = static_cast<unsigned char>(character);
                std::cout << hex[value >> 4] << hex[value & 15];
            }
            std::cout << '\n';
        }
        return std::cout ? 0 : 2;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
