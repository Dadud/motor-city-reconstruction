#include "mco/room_disconnect_flow.hpp"

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
        throw std::invalid_argument("truncated disconnect flow comparison header");
    std::uint32_t value = 0;
    for (unsigned i = 0; i < 4; ++i) value |= std::uint32_t(bytes[i]) << (8 * i);
    return value;
}
std::vector<std::uint8_t> read_image(std::uint32_t size) {
    std::vector<std::uint8_t> image(size);
    if (!std::cin.read(reinterpret_cast<char*>(image.data()), size))
        throw std::invalid_argument("truncated disconnect flow comparison image");
    return image;
}
void write_u32(std::uint32_t value) {
    for (unsigned i = 0; i < 4; ++i) std::cout.put(static_cast<char>((value >> (8 * i)) & 0xffu));
}
void snapshot(const mco::RoomDisconnectFlow& flow) {
    const auto action = flow.action();
    for (const auto value : {static_cast<std::uint32_t>(action.kind),
                            static_cast<std::uint32_t>(action.owner_offset.has_value()), action.owner_offset.value_or(0),
                            static_cast<std::uint32_t>(action.tracked),
                            static_cast<std::uint32_t>(action.operation_id.has_value()), action.operation_id.value_or(0),
                            static_cast<std::uint32_t>(action.result.has_value()), std::bit_cast<std::uint32_t>(action.result.value_or(0)),
                            static_cast<std::uint32_t>(action.argument.has_value())}) write_u32(value);
    if (action.argument) std::cout.write(reinterpret_cast<const char*>(action.argument->data()), action.argument->size());
    const auto image = flow.room_image();
    std::cout.write(reinterpret_cast<const char*>(image.data()), image.size());
}
} // namespace

int main() {
#ifdef _WIN32
    if (_setmode(_fileno(stdin), _O_BINARY) == -1 || _setmode(_fileno(stdout), _O_BINARY) == -1) return 2;
#endif
    try {
        const auto size = read_u32(), wait = read_u32(), count = read_u32();
        if (size < mco::room_disconnect_min_size || size > 65536 || wait > 1 || count > 10000)
            throw std::invalid_argument("disconnect flow comparison bounds exceeded");
        mco::RoomDisconnectFlow flow(read_image(size), wait != 0);
        snapshot(flow);
        for (std::uint32_t i = 0; i < count; ++i) {
            const auto command = read_u32(), present = read_u32(), bits = read_u32();
            if (present > 1) throw std::invalid_argument("invalid comparison presence flag");
            switch (command) {
            case 0: flow.container_reset(read_image(size)); break;
            case 1: flow.pending_yielded(read_image(size)); break;
            case 2: flow.enqueued(present ? std::optional<std::uint32_t>{bits} : std::nullopt); break;
            case 3: flow.completion_queried(present ? std::optional<std::int32_t>{std::bit_cast<std::int32_t>(bits)} : std::nullopt); break;
            case 4: flow.application_pumped(std::bit_cast<std::int32_t>(bits)); break;
            default: throw std::invalid_argument("unknown disconnect flow comparison command");
            }
            snapshot(flow);
        }
        if (std::cin.peek() != std::char_traits<char>::eof())
            throw std::invalid_argument("unexpected trailing disconnect flow comparison data");
        return std::cout ? 0 : 2;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
