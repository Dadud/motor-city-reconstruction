#pragma once
#include <array>
#include <bit>
#include <cstddef>
#include <cstdint>
#include <iostream>
#include <limits>
#include <sstream>
#include <span>
#include <stdexcept>
#include <string>

// One independent case per line; no implicit host endianness or pointer casts.
namespace cell_io {
inline std::uint32_t read(std::istream& input) {
    std::uint64_t value;
    if (!(input >> value) || value > std::numeric_limits<std::uint32_t>::max())
        throw std::invalid_argument("incomplete or invalid cell input");
    return static_cast<std::uint32_t>(value);
}
template<std::size_t N> auto image(std::istream& input) {
    std::array<std::byte, N> result{};
    for (auto& byte : result) {
        const auto value = read(input);
        if (value > 255) throw std::invalid_argument("invalid image byte");
        byte = static_cast<std::byte>(value);
    }
    return result;
}
inline void emit(std::uint32_t value) { std::cout << value << ' '; }
template<std::size_t N, std::size_t M>
auto view(std::array<std::byte,M>& bytes, std::size_t offset) {
    if (offset > M || N > M-offset)
        throw std::invalid_argument("comparison view outside backing image");
    return std::span<std::byte,N>(bytes.data()+offset, N);
}
template<class T, std::size_t N> void emit(const std::array<T, N>& values) {
    for (auto value : values) emit(static_cast<std::uint32_t>(value));
}
template<class Function> int run(Function function) {
    try {
        std::string line;
        std::size_t cases = 0;
        while (std::getline(std::cin, line)) {
            std::istringstream input(line);
            if (read(input) != 0) throw std::invalid_argument("invalid case marker");
            function(input);
            input >> std::ws;
            if (!input.eof()) throw std::invalid_argument("trailing cell input");
            std::cout << '\n';
            ++cases;
        }
        if (!cases) throw std::invalid_argument("empty cell comparison");
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
}  // namespace cell_io
