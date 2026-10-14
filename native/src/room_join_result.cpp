#include "mco/room_join_result.hpp"

#include <algorithm>
#include <stdexcept>

namespace mco {
namespace {
void validate(std::span<const std::uint8_t> image) {
    if (image.size() < room_worker_min_size)
        throw std::invalid_argument("expected complete room worker image");
}
std::uint32_t read32(std::span<const std::uint8_t> image, std::size_t offset) {
    std::uint32_t value = 0;
    for (std::size_t i = 0; i < 4; ++i) value |= std::uint32_t(image[offset+i]) << (8*i);
    return value;
}
void write32(std::vector<std::uint8_t>& image, std::size_t offset, std::uint32_t value) {
    for (std::size_t i = 0; i < 4; ++i) image[offset+i] = static_cast<std::uint8_t>(value >> (8*i));
}
}

RoomJoinCall room_join_call(std::span<const std::uint8_t> image,
                           std::span<const std::uint8_t> argument) {
    validate(image);
    if (argument.size() != channel_argument_size)
        throw std::invalid_argument("expected exact native room argument");
    RoomJoinCall call{read32(image,0x3b4),{},read32(image,0x3ac),read32(image,0x3b0)};
    std::copy(argument.begin(),argument.end(),call.argument.begin());
    return call;
}

RoomJoinTransition apply_room_join_result(std::span<const std::uint8_t> image,
                                         std::int32_t result) {
    validate(image);
    RoomJoinTransition transition{{image.begin(),image.end()},result,std::nullopt};
    write32(transition.worker_image,0x3a8,0);
    if (result < 0) {
        write32(transition.worker_image,0x3a4,static_cast<std::uint32_t>(result));
        return transition;
    }
    transition.worker_image[0xec] = 1;
    transition.worker_image[0xed] = 0;
    write32(transition.worker_image,0xc0,static_cast<std::uint32_t>(result));
    transition.return_code = 0;
    transition.notification = RoomJoinNotification{0x1fc,read32(image,0x39c),static_cast<std::uint32_t>(result)};
    return transition;
}

} // namespace mco
