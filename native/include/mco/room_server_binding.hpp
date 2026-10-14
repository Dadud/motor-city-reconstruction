#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <optional>
#include <span>
#include <vector>

namespace mco {
inline constexpr std::size_t network_owner_min_size = 0x6e0;
inline constexpr std::size_t embedded_room_offset = 0xa0;

struct ServerBindingTransition {
    std::vector<std::uint8_t> owner_image;
    std::int32_t return_code;
    bool mini_room_list_requested;
    std::optional<std::array<std::int32_t, 2>> notification;
};

// Private inert research image. Successful connection return becomes the room
// selector; this does not create connection handles, authenticate or enqueue.
ServerBindingTransition apply_server_connection_result(
    std::span<const std::uint8_t> owner_image, std::int32_t native_result);
} // namespace mco
