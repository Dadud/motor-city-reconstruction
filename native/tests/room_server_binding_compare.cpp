#include "mco/room_server_binding.hpp"

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
    std::array<unsigned char, 4> bytes{};
    if (!std::cin.read(reinterpret_cast<char*>(bytes.data()), bytes.size()))
        throw std::invalid_argument("truncated server binding comparison header");
    std::uint32_t value = 0;
    for (unsigned i = 0; i < 4; ++i) value |= std::uint32_t(bytes[i]) << (8 * i);
    return value;
}
void write_u32(std::uint32_t value) {
    for (unsigned i = 0; i < 4; ++i) std::cout.put(static_cast<char>((value >> (8 * i)) & 0xffu));
}
} // namespace

int main() {
#ifdef _WIN32
    if (_setmode(_fileno(stdin), _O_BINARY) == -1 || _setmode(_fileno(stdout), _O_BINARY) == -1) return 2;
#endif
    try {
        const auto size = read_u32();
        const auto result = std::bit_cast<std::int32_t>(read_u32());
        if (size > 1024 * 1024) throw std::invalid_argument("comparison image exceeds 1 MiB budget");
        std::vector<std::uint8_t> image(size);
        if (!std::cin.read(reinterpret_cast<char*>(image.data()), image.size()))
            throw std::invalid_argument("truncated server binding comparison image");
        if (std::cin.peek() != std::char_traits<char>::eof())
            throw std::invalid_argument("unexpected trailing server binding comparison data");
        const auto transition = mco::apply_server_connection_result(image, result);
        write_u32(std::bit_cast<std::uint32_t>(transition.return_code));
        write_u32(transition.mini_room_list_requested);
        write_u32(transition.notification.has_value());
        write_u32(transition.notification ? std::bit_cast<std::uint32_t>((*transition.notification)[0]) : 0);
        write_u32(transition.notification ? std::bit_cast<std::uint32_t>((*transition.notification)[1]) : 0);
        std::cout.write(reinterpret_cast<const char*>(transition.owner_image.data()), transition.owner_image.size());
        return std::cout ? 0 : 2;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
