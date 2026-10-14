#include "mco/room_selection.hpp"

#include <array>
#include <bit>
#include <cstdio>
#include <iostream>
#include <stdexcept>
#ifdef _WIN32
#include <fcntl.h>
#include <io.h>
#endif

namespace {
std::uint32_t read_u32() {
    std::array<unsigned char,4> bytes{};
    if (!std::cin.read(reinterpret_cast<char*>(bytes.data()), bytes.size()))
        throw std::invalid_argument("truncated room selection comparison header");
    std::uint32_t value = 0;
    for (unsigned i = 0; i < 4; ++i) value |= std::uint32_t(bytes[i]) << (8 * i);
    return value;
}
std::vector<std::uint8_t> read_image(std::uint32_t size) {
    if (size > 65536) throw std::invalid_argument("comparison image exceeds 65536");
    std::vector<std::uint8_t> image(size);
    if (size && !std::cin.read(reinterpret_cast<char*>(image.data()), size))
        throw std::invalid_argument("truncated room selection comparison image");
    return image;
}
void write_u32(std::uint32_t value) {
    for (unsigned i = 0; i < 4; ++i) std::cout.put(static_cast<char>((value >> (8 * i)) & 0xffu));
}
void emit(std::span<const std::uint8_t> image) {
    std::cout.write(reinterpret_cast<const char*>(image.data()), image.size());
}
} // namespace

int main() {
#ifdef _WIN32
    if (_setmode(_fileno(stdin), _O_BINARY) == -1 || _setmode(_fileno(stdout), _O_BINARY) == -1) return 2;
#endif
    try {
        const auto operation = read_u32();
        if (operation == 0) {
            const auto image = read_image(read_u32());
            if (std::cin.peek() != std::char_traits<char>::eof()) throw std::invalid_argument("trailing initializer comparison data");
            emit(mco::initialize_room_settings(image));
        } else if (operation == 1) {
            const auto room_size = read_u32(), name_size = read_u32(), cache_present = read_u32(), cache_size = read_u32();
            if (cache_present > 1 || (!cache_present && cache_size != 0)) throw std::invalid_argument("invalid cache presence");
            const auto room = read_image(room_size), name = read_image(name_size), cache = read_image(cache_size);
            if (std::cin.peek() != std::char_traits<char>::eof()) throw std::invalid_argument("trailing selection comparison data");
            const auto output = mco::select_room(room, name, cache_present
                ? std::optional<std::span<const std::uint8_t>>{cache} : std::nullopt);
            write_u32(std::bit_cast<std::uint32_t>(output.result));
            write_u32(static_cast<std::uint32_t>(output.source));
            emit(output.room_image);
        } else throw std::invalid_argument("unknown room selection comparison operation");
        return std::cout ? 0 : 2;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
