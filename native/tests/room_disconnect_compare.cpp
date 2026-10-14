#include "mco/room_disconnect.hpp"

#include <array>
#include <bit>
#include <cstdio>
#include <iostream>
#ifdef _WIN32
#include <fcntl.h>
#include <io.h>
#endif

namespace {
std::uint32_t read_u32() {
    std::array<unsigned char,4> bytes{};
    if (!std::cin.read(reinterpret_cast<char*>(bytes.data()), bytes.size()))
        throw std::invalid_argument("truncated disconnect comparison header");
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
        const auto size = read_u32(), wait = read_u32();
        if (size > 65536 || wait > 1) throw std::invalid_argument("invalid disconnect comparison size/wait");
        std::vector<std::uint8_t> image(size);
        if (size && !std::cin.read(reinterpret_cast<char*>(image.data()), size))
            throw std::invalid_argument("truncated disconnect comparison image");
        if (std::cin.peek() != std::char_traits<char>::eof())
            throw std::invalid_argument("unexpected trailing disconnect comparison data");
        const auto output = mco::prepare_room_disconnect(image, wait != 0);
        write_u32(output.argument.has_value()); write_u32(output.task_kind().value_or(0));
        write_u32(output.tracked); write_u32(output.immediate_return.has_value());
        write_u32(std::bit_cast<std::uint32_t>(output.immediate_return.value_or(0)));
        for (const auto offset : output.reset_owner_offsets) write_u32(offset);
        if (output.argument) std::cout.write(reinterpret_cast<const char*>(output.argument->data()), output.argument->size());
        std::cout.write(reinterpret_cast<const char*>(output.room_image.data()), output.room_image.size());
        return std::cout ? 0 : 2;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
