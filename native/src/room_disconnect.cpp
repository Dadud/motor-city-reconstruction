#include "mco/room_disconnect.hpp"

#include <algorithm>
#include <utility>

namespace mco {
namespace {
std::uint32_t read(std::span<const std::uint8_t> image, std::size_t offset, std::size_t size) {
    std::uint32_t value = 0;
    for (std::size_t i = 0; i < size; ++i) value |= static_cast<std::uint32_t>(image[offset + i]) << (8 * i);
    return value;
}
} // namespace

PendingRoomOperation::PendingRoomOperation()
    : std::invalid_argument("observe pending completion before preparing disconnect") {}

std::optional<std::uint32_t> RoomDisconnectPreparation::task_kind() const {
    return argument ? std::optional<std::uint32_t>{1} : std::nullopt;
}

RoomDisconnectPreparation prepare_room_disconnect(std::span<const std::uint8_t> room_image,
                                                  bool wait_for_completion) {
    if (room_image.size() < room_disconnect_min_size || room_image.size() > 65536)
        throw std::invalid_argument("expected bounded complete room image");
    const bool connected = read(room_image, 0xec, 2) != 0;
    const bool pending = read(room_image, 0x3a8, 4) != 0;
    if (connected && pending) throw PendingRoomOperation{};
    const bool tracked = connected && wait_for_completion;
    RoomDisconnectPreparation output{{room_image.begin(), room_image.end()}, std::nullopt,
        tracked, tracked ? std::nullopt : std::optional<std::int32_t>{0}};
    if (connected) {
        output.argument.emplace();
        std::copy_n(room_image.begin() + 0x39c, 4, output.argument->begin());
        std::copy_n(room_image.begin() + 0xc0, 4, output.argument->begin() + 4);
    }
    constexpr std::array<std::pair<std::size_t, std::size_t>, 11> cleared{{
        {0xa0,32},{0xd0,16},{0xf4,256},{0xc0,12},{0x1f4,4},
        {0xe2,2},{0xec,2},{0x1f8,2},{0xe6,2},{0xe8,4},{0xf0,4}}};
    for (const auto& [offset, count] : cleared)
        std::fill_n(output.room_image.begin() + offset, count, std::uint8_t{0});
    output.room_image[0xcc] = 0x21;
    std::fill_n(output.room_image.begin() + 0xcd, 3, std::uint8_t{0});
    output.room_image[0xe0] = 2;
    output.room_image[0xe1] = 0;
    output.room_image[0xe4] = 1;
    return output;
}
} // namespace mco
