#include "mco/room_server_binding.hpp"

#include <bit>
#include <stdexcept>

namespace mco {
namespace {
void write(std::vector<std::uint8_t>& image, std::size_t offset, std::uint32_t bits) {
    for (std::size_t i = 0; i < 4; ++i)
        image[offset + i] = static_cast<std::uint8_t>(bits >> (8 * i));
}
} // namespace

ServerBindingTransition apply_server_connection_result(
    std::span<const std::uint8_t> owner_image, std::int32_t native_result) {
    if (owner_image.size() < network_owner_min_size)
        throw std::invalid_argument("expected complete game network owner image");
    ServerBindingTransition output{{owner_image.begin(), owner_image.end()}, native_result, false, std::nullopt};
    const auto bits = std::bit_cast<std::uint32_t>(native_result);
    write(output.owner_image, 0x5cc, bits);
    write(output.owner_image, 0x600, 0);
    if (native_result < 0) {
        write(output.owner_image, 0x5f4, bits);
        return output;
    }
    write(output.owner_image, embedded_room_offset + 0x39c, bits);
    write(output.owner_image, 0x5fc, 1);
    output.mini_room_list_requested = true;
    output.notification = std::array<std::int32_t, 2>{native_result, 0};
    return output;
}
} // namespace mco
