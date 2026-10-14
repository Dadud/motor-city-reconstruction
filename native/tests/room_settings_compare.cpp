#include "mco/room_settings.hpp"

#include <array>
#include <cstdio>
#include <iostream>
#include <stdexcept>
#ifdef _WIN32
#include <fcntl.h>
#include <io.h>
#endif

namespace {
std::uint32_t read_size() {
    std::array<unsigned char, 4> bytes{};
    if (!std::cin.read(reinterpret_cast<char*>(bytes.data()), bytes.size()))
        throw std::invalid_argument("truncated settings comparison header");
    std::uint32_t value = 0;
    for (unsigned i = 0; i < 4; ++i) value |= std::uint32_t(bytes[i]) << (8 * i);
    if (value > 65536) throw std::invalid_argument("settings comparison image exceeds 65536");
    return value;
}
std::vector<std::uint8_t> read_image(std::uint32_t size) {
    std::vector<std::uint8_t> image(size);
    if (size && !std::cin.read(reinterpret_cast<char*>(image.data()), size))
        throw std::invalid_argument("truncated settings comparison image");
    return image;
}
} // namespace

int main() {
#ifdef _WIN32
    if (_setmode(_fileno(stdin), _O_BINARY) == -1 || _setmode(_fileno(stdout), _O_BINARY) == -1) return 2;
#endif
    try {
        const auto room_size = read_size();
        const auto settings_size = read_size();
        const auto room = read_image(room_size);
        const auto settings = read_image(settings_size);
        if (std::cin.peek() != std::char_traits<char>::eof())
            throw std::invalid_argument("unexpected trailing settings comparison data");
        const auto result = mco::apply_room_settings(room, settings);
        std::cout.write(reinterpret_cast<const char*>(result.data()), result.size());
        return std::cout ? 0 : 2;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
