#include "mco/lobby_channel_close.hpp"

#include <limits>
#include <stdexcept>

namespace mco {
namespace {
std::uint32_t checked(std::uint64_t value) {
    if (value > std::numeric_limits<std::uint32_t>::max())
        throw std::invalid_argument("channel-close value must fit uint32");
    return static_cast<std::uint32_t>(value);
}
} // namespace

std::array<std::uint8_t, 8> native_close_arguments(std::uint64_t server_selector,
                                                 std::uint64_t channel_id) {
    const auto selector = checked(server_selector), channel = checked(channel_id);
    std::array<std::uint8_t, 8> result{};
    for (unsigned i = 0; i < 4; ++i) {
        result[i] = static_cast<std::uint8_t>(selector >> (8 * i));
        result[i + 4] = static_cast<std::uint8_t>(channel >> (8 * i));
    }
    return result;
}
ChannelCloseRequest::ChannelCloseRequest(std::uint64_t channel_id) : channel_id_(checked(channel_id)) {}
std::uint32_t ChannelCloseRequest::channel_id() const noexcept { return channel_id_; }
std::array<std::uint8_t, 4> ChannelCloseRequest::payload() const noexcept {
    std::array<std::uint8_t, 4> result{};
    for (unsigned i = 0; i < 4; ++i) result[i] = static_cast<std::uint8_t>(channel_id_ >> (24 - 8 * i));
    return result;
}
NpsFrame ChannelCloseRequest::frame() const {
    const auto body = payload();
    return NpsFrame{0x105, {body.begin(), body.end()}};
}
} // namespace mco
